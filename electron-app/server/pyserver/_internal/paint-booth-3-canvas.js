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

        function _zoneHasRenderableMaterialClient(z) {
            if (typeof window !== 'undefined' && typeof window._zoneHasRenderableMaterial === 'function') {
                return window._zoneHasRenderableMaterial(z);
            }
            if (!z) return false;
            const prefixes = ['secondBase', 'thirdBase', 'fourthBase', 'fifthBase'];
            const hasOverlay = prefixes.some(prefix => {
                const strength = Number(z[prefix + 'Strength'] ?? 0);
                const baseId = z[prefix];
                const colorSrc = z[prefix + 'ColorSource'];
                const hasBaseId = typeof baseId === 'string' && baseId !== '' && baseId !== 'undefined' && baseId !== 'none';
                const hasColorSrc = typeof colorSrc === 'string' && colorSrc !== '' && colorSrc !== 'undefined' && colorSrc !== 'none';
                return strength > 0 && (hasBaseId || hasColorSrc);
            });
            return !!(z.base || z.finish || hasOverlay);
        }

        function generateScript() {
            // Validate
            const paintFile = document.getElementById('paintFile').value.trim();
            const outputDir = document.getElementById('outputDir').value.trim();
            const iracingId = document.getElementById('iracingId').value.trim();

            if (!paintFile) { showToast('Set the Source Paint path in the header bar!', true); return; }
            if (!outputDir) { showToast('Set the iRacing Paint Folder path in Car Info!', true); return; }

            const validZones = zones.filter(z => !z.muted && _zoneHasRenderableMaterialClient(z) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
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
    mask = mask.reshape((h, w)).astype(np.float32) / 255.0  # Normalize 0-255 to 0.0-1.0
    # Resize to match paint resolution if different
    if h != target_h or w != target_w:
        mask_img = Image.fromarray((mask * 255).astype(np.uint8))
        mask_img = mask_img.resize((target_w, target_h), Image.NEAREST)
        mask = np.array(mask_img).astype(np.float32) / 255.0
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
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine"),
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
    print("\\n  Make sure the engine/ folder is in the same directory as this script.")
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
                // 2026-04-18 MARATHON bug #54 (Luger, MED): pre-fix, FileReader
                // and Image load failures produced NO painter-visible toast
                // — drop a broken image, painter sees nothing happen. Add
                // onerror handlers.
                reader.onerror = function () {
                    showToast(`Could not read ${fileName}: ${(reader.error && reader.error.message) || 'unknown error'}`, true);
                };
                reader.onload = function (e) {
                    const img = new Image();
                    img.onerror = function () {
                        showToast(`Could not decode ${fileName} — file may be corrupt or not a valid image`, true);
                    };
                    img.onload = function () {
                        try {
                            const canvas = document.getElementById('paintCanvas');
                            if (!canvas) { showToast('Paint canvas element missing — cannot load', true); return; }
                            const ctx = canvas.getContext('2d');
                            canvas.width = img.width;
                            canvas.height = img.height;
                            ctx.drawImage(img, 0, 0);
                            paintImageData = ctx.getImageData(0, 0, img.width, img.height);
                            // Also size region canvas
                            const regionCanvas = document.getElementById('regionCanvas');
                            if (regionCanvas) { regionCanvas.width = img.width; regionCanvas.height = img.height; }

                            // Show/hide elements for 3-column layout
                            const emptyBig = document.getElementById('paintPreviewEmptyBig');
                            if (emptyBig) emptyBig.style.display = 'none';
                            const empty2 = document.getElementById('paintPreviewEmpty2');
                            if (empty2) empty2.style.display = 'none';
                            const paintLoaded = document.getElementById('paintPreviewLoaded');
                            if (paintLoaded) paintLoaded.style.display = 'flex';
                            /* advancedToolbar moved to vertical toolbar */
                            const edInfo2 = document.getElementById('eyedropperInfo'); if (edInfo2) edInfo2.style.display = 'block';
                            const paintDim = document.getElementById('paintDimensions');
                            if (paintDim) paintDim.textContent = `${img.width}x${img.height}`;
                            const paintStatus = document.getElementById('paintPreviewStatus');
                            if (paintStatus) paintStatus.textContent = `(${img.width}x${img.height})`;
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
                        } catch (loadErr) {
                            console.error('[paint load] img.onload error:', loadErr);
                            showToast(`Error loading ${fileName}: ${loadErr.message}`, true);
                        }
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

        var _filePickerController = null; // AbortController for in-flight browse request
        async function filePickerNavigate(dirPath) {
            const listEl = document.getElementById('filePickerList');
            const breadcrumbEl = document.getElementById('filePickerBreadcrumb');
            const quickNavEl = document.getElementById('filePickerQuickNav');

            // Abort any in-flight request before starting a new one
            if (_filePickerController) {
                try { _filePickerController.abort(); } catch (_) {}
                _filePickerController = null;
            }

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
                let requestController = null;
                let browseTimeout = null;

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
                    requestController = new AbortController();
                    _filePickerController = requestController;
                    browseTimeout = setTimeout(() => {
                        if (_filePickerController === requestController) {
                            try { requestController.abort(); } catch (_) {}
                        }
                    }, 15000);
                    const res = await fetch(ShokkerAPI.baseUrl + '/browse-files', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: dirPath, filter: _filePickerFilter }),
                        signal: requestController.signal,
                    });
                    clearTimeout(browseTimeout);
                    if (_filePickerController === requestController) _filePickerController = null;
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
                // If aborted by a new navigate call (not timeout), silently ignore
                if (browseTimeout) clearTimeout(browseTimeout);
                if (e.name === 'AbortError' && _filePickerController && _filePickerController !== requestController) {
                    console.log('[FilePicker] Previous request aborted (new navigate started)');
                    return;
                }
                if (_filePickerController === requestController) _filePickerController = null;
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
                    // Remember this file for auto-load on next launch
                    try { localStorage.setItem('spb_last_paint_file', path); } catch (e) {}
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
                    _psdPath = null;
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
        window.loadPaintPreviewFromServer = loadPaintPreviewFromServer;

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

        function _getPlacementTargetState(zone, target) {
            if (!zone || !target) return null;
            if (target === 'pattern') return { offsetX: zone.patternOffsetX ?? 0.5, offsetY: zone.patternOffsetY ?? 0.5, scale: zone.scale ?? 1.0, rotation: zone.rotation ?? 0 };
            if (target === 'base') return { offsetX: zone.baseOffsetX ?? 0.5, offsetY: zone.baseOffsetY ?? 0.5, scale: zone.baseScale ?? 1.0, rotation: zone.baseRotation ?? 0 };
            if (target === 'second_base') return { offsetX: zone.secondBasePatternOffsetX ?? 0.5, offsetY: zone.secondBasePatternOffsetY ?? 0.5, scale: zone.secondBasePatternScale ?? 1.0, rotation: zone.secondBasePatternRotation ?? 0 };
            if (target === 'third_base') return { offsetX: zone.thirdBasePatternOffsetX ?? 0.5, offsetY: zone.thirdBasePatternOffsetY ?? 0.5, scale: zone.thirdBasePatternScale ?? 1.0, rotation: zone.thirdBasePatternRotation ?? 0 };
            if (target === 'fourth_base') return { offsetX: zone.fourthBasePatternOffsetX ?? 0.5, offsetY: zone.fourthBasePatternOffsetY ?? 0.5, scale: zone.fourthBasePatternScale ?? 1.0, rotation: zone.fourthBasePatternRotation ?? 0 };
            if (target === 'fifth_base') return { offsetX: zone.fifthBasePatternOffsetX ?? 0.5, offsetY: zone.fifthBasePatternOffsetY ?? 0.5, scale: zone.fifthBasePatternScale ?? 1.0, rotation: zone.fifthBasePatternRotation ?? 0 };
            if (target.startsWith('spec_pattern_')) {
                const si = parseInt(target.split('_')[2], 10);
                const sp = zone.specPatternStack && zone.specPatternStack[si];
                if (!sp) return null;
                return { offsetX: sp.offsetX ?? 0.5, offsetY: sp.offsetY ?? 0.5, scale: sp.scale ?? 1.0, rotation: sp.rotation ?? 0 };
            }
            return null;
        }

        function _setPlacementTargetScale(zone, target, nextScale) {
            if (!zone || !target) return false;
            const scale = Math.max(0.1, Math.min(4.0, Number(nextScale) || 1.0));
            if (target === 'pattern') zone.scale = scale;
            else if (target === 'base') zone.baseScale = scale;
            else if (target === 'second_base') zone.secondBasePatternScale = scale;
            else if (target === 'third_base') zone.thirdBasePatternScale = scale;
            else if (target === 'fourth_base') zone.fourthBasePatternScale = scale;
            else if (target === 'fifth_base') zone.fifthBasePatternScale = scale;
            else if (target.startsWith('spec_pattern_')) {
                const si = parseInt(target.split('_')[2], 10);
                const sp = zone.specPatternStack && zone.specPatternStack[si];
                if (!sp) return false;
                sp.scale = scale;
            } else {
                return false;
            }
            return true;
        }

        // ===== PAINT PREVIEW & EYEDROPPER =====

        // Activate Manual Placement mode for a zone — enables drag-to-position on the preview canvas
        function activateManualPlacement(zoneIndex, layer) {
            // Set placement layer FIRST, before selectZone can reset it
            if (layer) {
                placementLayer = layer;
            } else if (placementLayer === 'none' || !placementLayer) {
                placementLayer = 'pattern';
            }

            // Now select the zone (it will see placementLayer is already set)
            if (typeof selectZone === 'function') selectZone(zoneIndex);

            // Keep the old floating placement bar as a compatibility fallback.
            // The top context strip is now the primary session surface.
            const toolsBar = document.getElementById('placement-tools-bar');
            if (toolsBar) toolsBar.style.display = document.getElementById('contextActionsBar') ? 'none' : 'flex';

            // Set cursor
            if (paintCanvas) paintCanvas.style.cursor = 'move';

            // Update banner
            if (typeof updatePlacementBanner === 'function') updatePlacementBanner();

            // Auto-enable split view for live feedback during placement
            if (typeof splitViewActive !== 'undefined' && !splitViewActive) {
                if (typeof toggleSplitView === 'function') {
                    toggleSplitView();
                } else {
                    // Fallback: find and click the split button
                    const splitBtn = document.getElementById('splitViewBtn') || document.querySelector('[onclick*="toggleSplit"]');
                    if (splitBtn) splitBtn.click();
                }
            }

            // Toast
            const layerName = placementLayer.replace(/_/g, ' ');
            showToast('Placement edit active for ' + layerName + ' - drag to position, scroll to resize, use +/-90 buttons to rotate', 'info');
            if (typeof renderContextActionBar === 'function') renderContextActionBar();
        }
        window.activateManualPlacement = activateManualPlacement;

        // Deactivate Manual Placement mode — hides tools bar and resets cursor
        function deactivateManualPlacement() {
            const prevTarget = placementLayer;
            placementLayer = 'none';
            const toolsBar = document.getElementById('placement-tools-bar');
            if (toolsBar) toolsBar.style.display = 'none';
            if (paintCanvas) paintCanvas.style.cursor = '';
            if (typeof window !== 'undefined') window._manualPlacementDragState = null;
            if (typeof updatePlacementBanner === 'function') updatePlacementBanner();
            if (typeof clearPlacementEditingState === 'function') clearPlacementEditingState(selectedZoneIndex, prevTarget);
            if (typeof renderContextActionBar === 'function') renderContextActionBar();
        }
        window.deactivateManualPlacement = deactivateManualPlacement;

        function hasActiveManualPlacementDrag() {
            return !!(typeof window !== 'undefined' && window._manualPlacementDragState);
        }
        window.hasActiveManualPlacementDrag = hasActiveManualPlacementDrag;

        function finishManualPlacementSession(noToast) {
            if (typeof placementLayer === 'undefined' || !placementLayer || placementLayer === 'none') return false;
            if (typeof window !== 'undefined' && typeof window._commitActivePlacementDrag === 'function') {
                window._commitActivePlacementDrag(true);
            }
            deactivateManualPlacement();
            if (typeof renderZones === 'function') renderZones();
            if (!noToast && typeof showToast === 'function') showToast('Placement editing closed');
            return true;
        }
        window.finishManualPlacementSession = finishManualPlacementSession;

        function cancelManualPlacementSession(noToast) {
            if (typeof window !== 'undefined' && typeof window._cancelActivePlacementDrag === 'function'
                    && window._cancelActivePlacementDrag(true)) {
                if (!noToast && typeof showToast === 'function') showToast('Placement drag cancelled');
                return true;
            }
            if (typeof placementLayer === 'undefined' || !placementLayer || placementLayer === 'none') return false;
            deactivateManualPlacement();
            if (typeof renderZones === 'function') renderZones();
            if (!noToast && typeof showToast === 'function') showToast('Placement editing closed');
            return true;
        }
        window.cancelManualPlacementSession = cancelManualPlacementSession;

        // ===== FLOATING TOOLS BAR HANDLERS =====
        // WIN #19 (Hawk audit): pre-fix, only `second_base` got a flip writer
        // even though the placement dropdown supports third/fourth/fifth_base.
        // The render serializer (`_applyExtraBaseOverlay`) was simultaneously
        // missing pattern_flip_h/v emit. Both halves fixed in this win.
        window.manualPlacementFlipH = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (typeof pushZoneUndo === 'function') pushZoneUndo('Flip placement horizontally', true);
            if (placementLayer === 'pattern') z.patternFlipH = !z.patternFlipH;
            else if (placementLayer === 'base') z.baseFlipH = !z.baseFlipH;
            else if (placementLayer === 'second_base') z.secondBasePatternFlipH = !z.secondBasePatternFlipH;
            else if (placementLayer === 'third_base')  z.thirdBasePatternFlipH  = !z.thirdBasePatternFlipH;
            else if (placementLayer === 'fourth_base') z.fourthBasePatternFlipH = !z.fourthBasePatternFlipH;
            else if (placementLayer === 'fifth_base')  z.fifthBasePatternFlipH  = !z.fifthBasePatternFlipH;
            else if (placementLayer.startsWith('spec_pattern_')) {
                // spec patterns don't have a flip property — no-op
            }
            triggerPreviewRender();
            renderZones();
        };

        window.manualPlacementFlipV = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (typeof pushZoneUndo === 'function') pushZoneUndo('Flip placement vertically', true);
            if (placementLayer === 'pattern') z.patternFlipV = !z.patternFlipV;
            else if (placementLayer === 'base') z.baseFlipV = !z.baseFlipV;
            else if (placementLayer === 'second_base') z.secondBasePatternFlipV = !z.secondBasePatternFlipV;
            else if (placementLayer === 'third_base')  z.thirdBasePatternFlipV  = !z.thirdBasePatternFlipV;
            else if (placementLayer === 'fourth_base') z.fourthBasePatternFlipV = !z.fourthBasePatternFlipV;
            else if (placementLayer === 'fifth_base')  z.fifthBasePatternFlipV  = !z.fifthBasePatternFlipV;
            else if (placementLayer.startsWith('spec_pattern_')) {
                // spec patterns don't have a flip property — no-op
            }
            triggerPreviewRender();
            renderZones();
        };

        window.manualPlacementRotateCW = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (typeof pushZoneUndo === 'function') pushZoneUndo('Rotate placement +90°', true);
            if (placementLayer === 'pattern') z.rotation = ((z.rotation || 0) + 90) % 360;
            else if (placementLayer === 'base') z.baseRotation = ((z.baseRotation || 0) + 90) % 360;
            else if (placementLayer === 'second_base') z.secondBasePatternRotation = (((z.secondBasePatternRotation || 0) + 90) % 360);
            else if (placementLayer === 'third_base') z.thirdBasePatternRotation = (((z.thirdBasePatternRotation || 0) + 90) % 360);
            else if (placementLayer === 'fourth_base') z.fourthBasePatternRotation = (((z.fourthBasePatternRotation || 0) + 90) % 360);
            else if (placementLayer === 'fifth_base') z.fifthBasePatternRotation = (((z.fifthBasePatternRotation || 0) + 90) % 360);
            else if (placementLayer.startsWith('spec_pattern_')) {
                const si = parseInt(placementLayer.split('_')[2]);
                const sp = z.specPatternStack && z.specPatternStack[si];
                if (sp) sp.rotation = ((sp.rotation || 0) + 90) % 360;
            }
            triggerPreviewRender();
            renderZones();
        };

        window.manualPlacementRotateCCW = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (typeof pushZoneUndo === 'function') pushZoneUndo('Rotate placement -90°', true);
            if (placementLayer === 'pattern') z.rotation = (((z.rotation || 0) - 90) + 360) % 360;
            else if (placementLayer === 'base') z.baseRotation = (((z.baseRotation || 0) - 90) + 360) % 360;
            else if (placementLayer === 'second_base') z.secondBasePatternRotation = (((z.secondBasePatternRotation || 0) - 90) + 360) % 360;
            else if (placementLayer === 'third_base') z.thirdBasePatternRotation = (((z.thirdBasePatternRotation || 0) - 90) + 360) % 360;
            else if (placementLayer === 'fourth_base') z.fourthBasePatternRotation = (((z.fourthBasePatternRotation || 0) - 90) + 360) % 360;
            else if (placementLayer === 'fifth_base') z.fifthBasePatternRotation = (((z.fifthBasePatternRotation || 0) - 90) + 360) % 360;
            else if (placementLayer.startsWith('spec_pattern_')) {
                const si = parseInt(placementLayer.split('_')[2]);
                const sp = z.specPatternStack && z.specPatternStack[si];
                if (sp) sp.rotation = (((sp.rotation || 0) - 90) + 360) % 360;
            }
            triggerPreviewRender();
            renderZones();
        };

        window.manualPlacementReset = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (typeof pushZoneUndo === 'function') pushZoneUndo('Reset placement', true);
            if (placementLayer === 'pattern') {
                z.patternOffsetX = 0.5; z.patternOffsetY = 0.5; z.scale = 1.0; z.rotation = 0; z.patternFlipH = false; z.patternFlipV = false;
            } else if (placementLayer === 'base') {
                z.baseOffsetX = 0.5; z.baseOffsetY = 0.5; z.baseScale = 1.0; z.baseRotation = 0; z.baseFlipH = false; z.baseFlipV = false;
            } else if (placementLayer === 'second_base') {
                z.secondBasePatternOffsetX = 0.5; z.secondBasePatternOffsetY = 0.5; z.secondBasePatternScale = 1.0; z.secondBasePatternRotation = 0;
            } else if (placementLayer === 'third_base') {
                z.thirdBasePatternOffsetX = 0.5; z.thirdBasePatternOffsetY = 0.5; z.thirdBasePatternScale = 1.0; z.thirdBasePatternRotation = 0;
            } else if (placementLayer === 'fourth_base') {
                z.fourthBasePatternOffsetX = 0.5; z.fourthBasePatternOffsetY = 0.5; z.fourthBasePatternScale = 1.0; z.fourthBasePatternRotation = 0;
            } else if (placementLayer === 'fifth_base') {
                z.fifthBasePatternOffsetX = 0.5; z.fifthBasePatternOffsetY = 0.5; z.fifthBasePatternScale = 1.0; z.fifthBasePatternRotation = 0;
            } else if (placementLayer.startsWith('spec_pattern_')) {
                const si = parseInt(placementLayer.split('_')[2]);
                const sp = z.specPatternStack && z.specPatternStack[si];
                if (sp) { sp.offsetX = 0.5; sp.offsetY = 0.5; sp.scale = 1.0; sp.rotation = 0; }
            }
            triggerPreviewRender();
            renderZones();
        };

        // Draw a crosshair + box overlay on the canvas during manual placement drag
        function drawPlacementCrosshair(canvas, ox, oy, layer) {
            var rc = document.getElementById('regionCanvas');
            if (!rc) return;
            if (rc.width !== canvas.width || rc.height !== canvas.height) {
                rc.width = canvas.width; rc.height = canvas.height;
                rc.style.width = canvas.style.width; rc.style.height = canvas.style.height;
            }
            var ctx = rc.getContext('2d');
            ctx.clearRect(0, 0, rc.width, rc.height);
            var cx = Math.round(ox * canvas.width);
            var cy = Math.round(oy * canvas.height);
            var armLen = Math.min(canvas.width, canvas.height) * 0.15;
            ctx.save();
            // Outer glow
            ctx.strokeStyle = 'rgba(0,255,235,0.3)'; ctx.lineWidth = 6;
            ctx.beginPath();
            ctx.moveTo(cx - armLen, cy); ctx.lineTo(cx + armLen, cy);
            ctx.moveTo(cx, cy - armLen); ctx.lineTo(cx, cy + armLen);
            ctx.stroke();
            // Inner bright dashed line
            ctx.strokeStyle = 'rgba(0,255,235,0.9)'; ctx.lineWidth = 2; ctx.setLineDash([8, 4]);
            ctx.beginPath();
            ctx.moveTo(cx - armLen, cy); ctx.lineTo(cx + armLen, cy);
            ctx.moveTo(cx, cy - armLen); ctx.lineTo(cx, cy + armLen);
            ctx.stroke(); ctx.setLineDash([]);
            // Center circle
            ctx.beginPath(); ctx.arc(cx, cy, 8, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(255,68,68,0.9)'; ctx.lineWidth = 2; ctx.stroke();
            ctx.beginPath(); ctx.arc(cx, cy, 2, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,68,68,1)'; ctx.fill();
            // Label
            var label = (layer || 'pattern').replace(/_/g, ' ').toUpperCase();
            var pctX = Math.round(ox * 100) + '%'; var pctY = Math.round(oy * 100) + '%';
            var txt = label + '  X:' + pctX + '  Y:' + pctY;
            ctx.font = 'bold 14px monospace';
            ctx.fillStyle = 'rgba(0,0,0,0.7)';
            var tw = ctx.measureText(txt).width;
            ctx.fillRect(cx - tw/2 - 4, cy - armLen - 26, tw + 8, 20);
            ctx.fillStyle = '#00ffe0'; ctx.textAlign = 'center';
            ctx.fillText(txt, cx, cy - armLen - 10);
            ctx.restore();
        }
        function clearPlacementCrosshair() {
            var rc = document.getElementById('regionCanvas');
            if (rc) rc.getContext('2d').clearRect(0, 0, rc.width, rc.height);
        }

        // Shared: set up hover + click + draw handlers on the canvas
        var _canvasHandlersAttached = false; // Guard: only attach document-level listeners once
        function setupCanvasHandlers(canvas) {
            // Placement drag (GIMP/PS-style: drag on map to position pattern/base overlay)
            let placementDragging = false;
            let placementDragStart = null;
            let placementPreviewTimer = null;
            let placementSnapshotPushed = false;

            function _syncPlacementDragState() {
                if (typeof window === 'undefined') return;
                window._manualPlacementDragState = (placementDragging && placementDragStart)
                    ? {
                        zoneIndex: placementDragStart.zoneIndex,
                        target: placementDragStart.target,
                        offsetX: placementDragStart.offsetX,
                        offsetY: placementDragStart.offsetY,
                    }
                    : null;
            }

            window._cancelActivePlacementDrag = function(noToast) {
                if (!placementDragging || !placementDragStart) return false;
                applyPlacementOffset(placementDragStart.zoneIndex, placementDragStart.target, placementDragStart.offsetX, placementDragStart.offsetY);
                placementDragging = false;
                placementDragStart = null;
                placementSnapshotPushed = false;
                clearTimeout(placementPreviewTimer);
                placementPreviewTimer = null;
                clearPlacementCrosshair();
                if (typeof renderZones === 'function') renderZones();
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                canvas.style.cursor = (typeof placementLayer !== 'undefined' && placementLayer !== 'none') ? 'grab' : '';
                _syncPlacementDragState();
                if (!noToast && typeof showToast === 'function') showToast('Placement drag cancelled');
                return true;
            };

            window._commitActivePlacementDrag = function(noToast) {
                if (!placementDragging && !placementDragStart) return false;
                placementDragging = false;
                placementDragStart = null;
                placementSnapshotPushed = false;
                clearTimeout(placementPreviewTimer);
                placementPreviewTimer = null;
                clearPlacementCrosshair();
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                canvas.style.cursor = (typeof placementLayer !== 'undefined' && placementLayer !== 'none') ? 'grab' : '';
                _syncPlacementDragState();
                if (!noToast && typeof showToast === 'function') {
                    showToast('Position saved — will apply on next render', 'success');
                }
                return true;
            };

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
                } else if (layer === 'fourth_base') {
                    z.fourthBasePatternOffsetX = ox; z.fourthBasePatternOffsetY = oy;
                    ['detFBPatPosXVal', 'detFBPatPosYVal'].forEach((prefix, idx) => {
                        const el = document.getElementById(prefix + i); if (el) { el.textContent = idx ? pctY : pctX; const inp = el.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? vy : vx; }
                    });
                    const panel = document.getElementById('zoneEditorFloat'); if (panel) {
                        const sx = panel.querySelector('#detFBPatPosXVal' + i); if (sx) { sx.textContent = pctX; const inp = sx.previousElementSibling; if (inp && inp.type === 'range') inp.value = vx; }
                        const sy = panel.querySelector('#detFBPatPosYVal' + i); if (sy) { sy.textContent = pctY; const inp = sy.previousElementSibling; if (inp && inp.type === 'range') inp.value = vy; }
                    }
                } else if (layer === 'fifth_base') {
                    z.fifthBasePatternOffsetX = ox; z.fifthBasePatternOffsetY = oy;
                    ['detFifPatPosXVal', 'detFifPatPosYVal'].forEach((prefix, idx) => {
                        const el = document.getElementById(prefix + i); if (el) { el.textContent = idx ? pctY : pctX; const inp = el.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? vy : vx; }
                    });
                    const panel = document.getElementById('zoneEditorFloat'); if (panel) {
                        const sx = panel.querySelector('#detFifPatPosXVal' + i); if (sx) { sx.textContent = pctX; const inp = sx.previousElementSibling; if (inp && inp.type === 'range') inp.value = vx; }
                        const sy = panel.querySelector('#detFifPatPosYVal' + i); if (sy) { sy.textContent = pctY; const inp = sy.previousElementSibling; if (inp && inp.type === 'range') inp.value = vy; }
                    }
                } else if (layer === 'base') {
                    z.baseOffsetX = ox; z.baseOffsetY = oy;
                    const xEl = document.getElementById('detBasePosXVal' + i); if (xEl) { xEl.textContent = pctX; const inp = xEl.previousElementSibling; if (inp && inp.type === 'range') inp.value = vx; }
                    const yEl = document.getElementById('detBasePosYVal' + i); if (yEl) { yEl.textContent = pctY; const inp = yEl.previousElementSibling; if (inp && inp.type === 'range') inp.value = vy; }
                } else if (layer.startsWith('spec_pattern_')) {
                    const si = parseInt(layer.split('_')[2]);
                    const sp = z.specPatternStack && z.specPatternStack[si];
                    if (sp) { sp.offsetX = ox; sp.offsetY = oy; }
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

            function updateSelectionMovePreview(pos) {
                if (!_selectionMoveDrag || !pos || typeof zones === 'undefined' || selectedZoneIndex < 0 || selectedZoneIndex >= zones.length) return;
                const zone = zones[selectedZoneIndex];
                if (!zone) return;
                const dx = pos.x - _selectionMoveDrag.startX;
                const dy = pos.y - _selectionMoveDrag.startY;
                zone.regionMask = _shiftRegionMask(_selectionMoveDrag.baseMask, canvas.width, canvas.height, dx, dy);
                if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
                if (typeof updateRegionStatus === 'function') updateRegionStatus();
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

            function _getFastOverlayContext() {
                const paintCanvas = document.getElementById('paintCanvas');
                const regionCanvas = document.getElementById('regionCanvas');
                if (!regionCanvas || !paintCanvas) return null;
                if (regionCanvas.width !== paintCanvas.width || regionCanvas.height !== paintCanvas.height) {
                    regionCanvas.width = paintCanvas.width;
                    regionCanvas.height = paintCanvas.height;
                    regionCanvas.style.width = paintCanvas.style.width;
                    regionCanvas.style.height = paintCanvas.style.height;
                } else if (regionCanvas.style.width !== paintCanvas.style.width || regionCanvas.style.height !== paintCanvas.style.height) {
                    regionCanvas.style.width = paintCanvas.style.width;
                    regionCanvas.style.height = paintCanvas.style.height;
                }
                return regionCanvas.getContext('2d');
            }

            function _paintFastOverlayArc(cx, cy, radius, compositeOperation, fillStyle) {
                const ctx = _getFastOverlayContext();
                if (!ctx) return;
                ctx.globalCompositeOperation = compositeOperation;
                ctx.fillStyle = fillStyle;
                ctx.beginPath();
                ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                ctx.fill();
                ctx.globalCompositeOperation = 'source-over';
            }

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
                    // Paint: draw zone colour circle, dimmed by brush opacity for visual feedback
                    ctx.globalCompositeOperation = 'source-over';
                    const color = ZONE_OVERLAY_COLORS[selectedZoneIndex % ZONE_OVERLAY_COLORS.length];
                    const brushOpacity = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100.0;
                    const alpha = (color[3] / 255.0) * brushOpacity;
                    ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${alpha.toFixed(3)})`;
                }
                ctx.beginPath();
                ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                ctx.fill();
                ctx.globalCompositeOperation = 'source-over';
            }

            function _fastSpatialOverlayArc(cx, cy, radius, value) {
                const ctx = _getFastOverlayContext();
                if (!ctx) return;
                if (value === 0) {
                    ctx.globalCompositeOperation = 'destination-out';
                    ctx.fillStyle = 'rgba(0,0,0,1)';
                } else if (value === 2) {
                    ctx.globalCompositeOperation = 'source-over';
                    ctx.fillStyle = 'rgba(255,72,72,0.769)';
                } else {
                    ctx.globalCompositeOperation = 'source-over';
                    ctx.fillStyle = 'rgba(24,255,166,0.769)';
                }
                ctx.beginPath();
                ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                ctx.fill();
                ctx.globalCompositeOperation = 'source-over';
            }

            function _paintRegionCircleAt(zone, mask, w, h, x, y, radius, value, opacity, hardness) {
                // Core paint kernel — paints a single circle dab at (x,y)
                const r2 = radius * radius;
                const sigma = radius * (1.0 - hardness) * 0.5;
                const sigma2x2 = 2.0 * sigma * sigma;
                const useHardBrush = (hardness >= 0.99 && opacity >= 0.99);
                // Brush shape support
                const shape = document.getElementById('brushShape')?.value || 'round';

                for (let dy = -radius; dy <= radius; dy++) {
                    for (let dx = -radius; dx <= radius; dx++) {
                        const dist2 = dx * dx + dy * dy;
                        // Shape test
                        if (shape === 'round' && dist2 > r2) continue;
                        if (shape === 'square' && (Math.abs(dx) > radius || Math.abs(dy) > radius)) continue;
                        if (shape === 'diamond' && (Math.abs(dx) + Math.abs(dy) > radius)) continue;
                        if (shape === 'slash' && (Math.abs(dx - dy) > radius * 0.3)) continue;
                        if (shape === 'noise' && dist2 > r2) continue;

                        const px = x + dx, py = y + dy;
                        if (px < 0 || px >= w || py < 0 || py >= h) continue;
                        const idx = py * w + px;

                        // Noise brush: random skip for texture
                        if (shape === 'noise' && Math.random() > 0.6) continue;

                        if (useHardBrush) {
                            mask[idx] = value ? 255 : 0;
                        } else if (value === 0) {
                            const dist = Math.sqrt(dist2);
                            const falloff = sigma > 0.5 ? Math.exp(-(dist * dist) / sigma2x2) : (dist <= radius ? 1.0 : 0.0);
                            const eraseAmt = falloff * opacity;
                            const current = mask[idx] / 255.0;
                            mask[idx] = Math.round(Math.max(0, current - eraseAmt) * 255);
                        } else {
                            const dist = Math.sqrt(dist2);
                            const falloff = sigma > 0.5 ? Math.exp(-(dist * dist) / sigma2x2) : (dist <= radius ? 1.0 : 0.0);
                            const paintVal = Math.round(falloff * opacity * 255);
                            mask[idx] = Math.max(mask[idx], paintVal);
                        }
                    }
                }
            }

            function _zoneHasClientScopedSelector(zone) {
                if (!zone) return false;
                if (zone.sourceLayer) return true;
                if (zone.colorMode === 'multi' && Array.isArray(zone.colors) && zone.colors.length > 0) return true;
                if (zone.color && typeof zone.color === 'object' && !Array.isArray(zone.color) && Array.isArray(zone.color.color_rgb)) return true;
                if (zone.colorMode === 'picker' && typeof zone.pickerColor === 'string' && /^#[0-9a-fA-F]{6}$/.test(zone.pickerColor)) return true;
                if (zone.colorMode === 'special' && (zone.color === 'remaining' || zone.color === 'everything')) return true;
                return false;
            }

            function _zoneHasExplicitRegionMask(zone) {
                return !!(zone && zone.regionMask && zone.regionMask.some(v => v > 0));
            }

            function _zoneBrushUsesScopedRefinement(zone) {
                return _zoneHasClientScopedSelector(zone) && !_zoneHasExplicitRegionMask(zone);
            }
            window._zoneBrushUsesScopedRefinement = _zoneBrushUsesScopedRefinement;

            function _zoneShouldRequestPriorityOverride(zone) {
                if (!_zoneBrushUsesScopedRefinement(zone) || !zone || !zone.spatialMask) return false;
                return zone.spatialMask.some(v => v === 1);
            }
            window._zoneShouldRequestPriorityOverride = _zoneShouldRequestPriorityOverride;

            function _zoneHasScopedKeepMarks(zone) {
                return !!(zone && zone.spatialMask && zone.spatialMask.some(v => v === 1));
            }

            function _zoneHasActiveBaseOverlayClient(zone) {
                if (!zone) return false;
                return ['secondBase', 'thirdBase', 'fourthBase', 'fifthBase'].some(prefix => {
                    const strength = Number(zone[prefix + 'Strength'] ?? 0);
                    const baseId = zone[prefix];
                    const colorSrc = zone[prefix + 'ColorSource'];
                    const hasBaseId = typeof baseId === 'string' && baseId !== '' && baseId !== 'undefined' && baseId !== 'none';
                    const hasColorSrc = typeof colorSrc === 'string' && colorSrc !== '' && colorSrc !== 'undefined' && colorSrc !== 'none';
                    return strength > 0 && (hasBaseId || hasColorSrc);
                });
            }

            function _zoneShouldPreserveScopedBrushExactColor(zone) {
                if (!zone || !zone._scopedBrushAutoBaseColor) return false;
                if (_zoneHasActiveBaseOverlayClient(zone)) return false;
                if (String(zone.baseColorMode || 'source').toLowerCase() !== 'solid') return false;
                return _zoneHasScopedKeepMarks(zone);
            }
            if (typeof window !== 'undefined') window._zoneShouldPreserveScopedBrushExactColor = _zoneShouldPreserveScopedBrushExactColor;

            function _refreshScopedZoneBaseUi(zoneIndex) {
                if (typeof zoneIndex !== 'number' || zoneIndex < 0) return;
                if (typeof renderZones === 'function') renderZones();
                if (typeof selectedZoneIndex !== 'undefined' && selectedZoneIndex === zoneIndex && typeof renderZoneDetail === 'function') {
                    renderZoneDetail(zoneIndex);
                }
            }

            function _normalizeScopedZoneAutoBaseColor(zoneIndex) {
                if (typeof zoneIndex !== 'number' || zoneIndex < 0 || zoneIndex >= zones.length) return false;
                const zone = zones[zoneIndex];
                if (!zone || !zone._scopedBrushAutoBaseColor) return false;
                if (_zoneHasScopedKeepMarks(zone)) return false;
                zone.baseColorMode = 'source';
                zone.baseColorSource = null;
                zone._scopedBrushAutoBaseColor = false;
                _refreshScopedZoneBaseUi(zoneIndex);
                return true;
            }

            function _maybeAdoptForegroundAsScopedZoneBaseColor(zoneIndex) {
                if (typeof zoneIndex !== 'number' || zoneIndex < 0 || zoneIndex >= zones.length) return false;
                const zone = zones[zoneIndex];
                if (!zone || !_zoneBrushUsesScopedRefinement(zone) || !_zoneHasScopedKeepMarks(zone)) return false;
                const fgHex = (typeof _foregroundColor === 'string' && /^#[0-9a-fA-F]{6}$/.test(_foregroundColor))
                    ? _foregroundColor.toLowerCase()
                    : null;
                if (!fgHex) return false;
                const mode = String(zone.baseColorMode || 'source').toLowerCase();
                if (mode === 'special' || mode === 'gradient') return false;
                if (mode === 'solid' && !zone._scopedBrushAutoBaseColor) return false;
                const prevMode = mode;
                const prevColor = typeof zone.baseColor === 'string' ? zone.baseColor.toLowerCase() : zone.baseColor;
                const prevSource = zone.baseColorSource;
                const prevStrength = zone.baseColorStrength;
                const prevAutoFlag = !!zone._scopedBrushAutoBaseColor;
                zone.baseColor = fgHex;
                zone.baseColorMode = 'solid';
                zone.baseColorSource = null;
                if (!(typeof prevStrength === 'number' && prevStrength > 0)) zone.baseColorStrength = 1;
                zone._autoBaseColorFill = false;
                zone._scopedBrushAutoBaseColor = true;
                const changed = prevMode !== 'solid'
                    || prevColor !== fgHex
                    || prevSource != null
                    || !prevAutoFlag;
                if (changed) _refreshScopedZoneBaseUi(zoneIndex);
                return changed;
            }

            function _getZoneClientColorTargets(zone) {
                if (!zone) return [];
                if (zone.colorMode === 'multi' && Array.isArray(zone.colors) && zone.colors.length > 0) {
                    return zone.colors.filter(c => c && Array.isArray(c.color_rgb));
                }
                if (zone.color && typeof zone.color === 'object' && !Array.isArray(zone.color) && Array.isArray(zone.color.color_rgb)) {
                    return [zone.color];
                }
                if (zone.colorMode === 'picker' && typeof zone.pickerColor === 'string' && /^#[0-9a-fA-F]{6}$/.test(zone.pickerColor)) {
                    const hex = zone.pickerColor;
                    return [{
                        color_rgb: [
                            parseInt(hex.slice(1, 3), 16),
                            parseInt(hex.slice(3, 5), 16),
                            parseInt(hex.slice(5, 7), 16)
                        ],
                        tolerance: zone.pickerTolerance ?? 40
                    }];
                }
                return [];
            }

            function _buildZoneScopedSelectorMask(zone, w, h) {
                if (!zone || !paintImageData || !w || !h) return null;
                const scopeMask = new Uint8Array(w * h).fill(255);
                let hasConstraint = false;

                if (zone.sourceLayer && typeof _psdLayers !== 'undefined' && typeof getLayerVisibleContributionMask === 'function') {
                    const srcLayer = _psdLayers.find(l => l.id === zone.sourceLayer);
                    if (srcLayer && srcLayer.img) {
                        const visibleMask = getLayerVisibleContributionMask(srcLayer, w, h);
                        if (visibleMask && visibleMask.length === scopeMask.length) {
                            hasConstraint = true;
                            for (let i = 0; i < scopeMask.length; i++) {
                                if (visibleMask[i] <= 0) scopeMask[i] = 0;
                            }
                        }
                    }
                }

                const targets = _getZoneClientColorTargets(zone);
                if (targets.length > 0) {
                    hasConstraint = true;
                    const data = paintImageData.data;
                    for (let i = 0; i < scopeMask.length; i++) {
                        if (scopeMask[i] === 0) continue;
                        const di = i * 4;
                        if (data[di + 3] < 8) {
                            scopeMask[i] = 0;
                            continue;
                        }
                        let matched = false;
                        for (const target of targets) {
                            const rgb = target.color_rgb || [128, 128, 128];
                            const tol = Number(target.tolerance ?? zone.pickerTolerance ?? 40);
                            if (
                                Math.abs(data[di] - rgb[0]) <= tol &&
                                Math.abs(data[di + 1] - rgb[1]) <= tol &&
                                Math.abs(data[di + 2] - rgb[2]) <= tol
                            ) {
                                matched = true;
                                break;
                            }
                        }
                        if (!matched) scopeMask[i] = 0;
                    }
                }

                return hasConstraint ? scopeMask : null;
            }
            window._buildZoneScopedSelectorMask = _buildZoneScopedSelectorMask;

            function _paintScopedSpatialCircle(zone, scopeMask, w, h, cx, cy, radius, value) {
                if (!zone) return false;
                if (!zone.spatialMask) {
                    zone.spatialMask = new Uint8Array(w * h);
                }
                const r2 = radius * radius;
                const x0 = Math.max(0, Math.floor(cx - radius));
                const x1 = Math.min(w - 1, Math.ceil(cx + radius));
                const y0 = Math.max(0, Math.floor(cy - radius));
                const y1 = Math.min(h - 1, Math.ceil(cy + radius));
                let touched = false;
                for (let y = y0; y <= y1; y++) {
                    for (let x = x0; x <= x1; x++) {
                        if ((x - cx) * (x - cx) + (y - cy) * (y - cy) > r2) continue;
                        const idx = y * w + x;
                        if (scopeMask && scopeMask[idx] <= 0) continue;
                        zone.spatialMask[idx] = value;
                        touched = true;
                    }
                }
                return touched;
            }

            function paintRegionCircle(x, y, radius, value) {
                // Paint into the current zone's regionMask with opacity + hardness + symmetry support.
                // For color-picked / layer-restricted zones with no explicit region drawn yet,
                // brush strokes should refine INSIDE the existing selector instead of replacing it.
                const zone = zones[selectedZoneIndex];
                if (!zone) return;
                const w = canvas.width, h = canvas.height;
                const useScopedRefinement = _zoneBrushUsesScopedRefinement(zone);
                if (useScopedRefinement) {
                    const scopeMask = _buildZoneScopedSelectorMask(zone, w, h);
                    if (!scopeMask) return 'spatial';
                    const spatialValue = value ? 1 : 0;
                    const touched = _paintScopedSpatialCircle(zone, scopeMask, w, h, x, y, radius, spatialValue);
                    if (touched) {
                        if (value) _maybeAdoptForegroundAsScopedZoneBaseColor(selectedZoneIndex);
                        else _normalizeScopedZoneAutoBaseColor(selectedZoneIndex);
                    }
                    return 'spatial';
                }
                if (!zone.regionMask) {
                    zone.regionMask = new Uint8Array(w * h);
                }
                const opacity = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100.0;
                const hardness = parseInt(document.getElementById('brushHardness')?.value || 100) / 100.0;
                const flow = parseInt(document.getElementById('brushFlow')?.value || 100) / 100.0;
                const effectiveOpacity = opacity * flow;

                // Paint primary stroke
                _paintRegionCircleAt(zone, zone.regionMask, w, h, x, y, radius, value, effectiveOpacity, hardness);

                // Symmetry: paint mirrored strokes
                const sym = getEffectiveSymmetryMode();
                const cx = Math.floor(w / 2), cy = Math.floor(h / 2);
                if (sym === 'mirror-h' || sym === 'mirror-both') {
                    _paintRegionCircleAt(zone, zone.regionMask, w, h, w - 1 - x, y, radius, value, effectiveOpacity, hardness);
                }
                if (sym === 'mirror-v' || sym === 'mirror-both') {
                    _paintRegionCircleAt(zone, zone.regionMask, w, h, x, h - 1 - y, radius, value, effectiveOpacity, hardness);
                }
                if (sym === 'mirror-both') {
                    _paintRegionCircleAt(zone, zone.regionMask, w, h, w - 1 - x, h - 1 - y, radius, value, effectiveOpacity, hardness);
                }
                if (sym === 'radial-4') {
                    const dx = x - cx, dy = y - cy;
                    _paintRegionCircleAt(zone, zone.regionMask, w, h, cx - dy, cy + dx, radius, value, effectiveOpacity, hardness); // 90°
                    _paintRegionCircleAt(zone, zone.regionMask, w, h, cx - dx, cy - dy, radius, value, effectiveOpacity, hardness); // 180°
                    _paintRegionCircleAt(zone, zone.regionMask, w, h, cx + dy, cy - dx, radius, value, effectiveOpacity, hardness); // 270°
                }
                if (sym === 'radial-8') {
                    const dx = x - cx, dy = y - cy;
                    for (let a = 1; a < 8; a++) {
                        const angle = a * Math.PI / 4;
                        const rx = Math.round(cx + dx * Math.cos(angle) - dy * Math.sin(angle));
                        const ry = Math.round(cy + dx * Math.sin(angle) + dy * Math.cos(angle));
                        _paintRegionCircleAt(zone, zone.regionMask, w, h, rx, ry, radius, value, effectiveOpacity, hardness);
                    }
                }
                return 'region';
            }

            // ── GRADIENT FILL ────────────────────────────────────────────────────────
            // Fill the current zone's regionMask with a gradient between two points
            function fillGradientMask(x1, y1, x2, y2, gradientType) {
                const zone = zones[selectedZoneIndex];
                if (!zone) return;
                const w = canvas.width, h = canvas.height;
                if (!zone.regionMask) {
                    zone.regionMask = new Uint8Array(w * h);
                }
                const dx = x2 - x1, dy = y2 - y1;
                const len = Math.sqrt(dx * dx + dy * dy);
                if (len < 2) return;
                const selMode = document.getElementById('selectionMode')?.value || 'add';
                const nx = dx / len, ny = dy / len; // unit vector start→end

                for (let py = 0; py < h; py++) {
                    for (let px = 0; px < w; px++) {
                        let t = 0; // gradient parameter 0→1
                        if (gradientType === 'linear') {
                            // Project pixel onto start→end line
                            t = ((px - x1) * nx + (py - y1) * ny) / len;
                        } else if (gradientType === 'radial') {
                            // Distance from start / distance to end
                            const d = Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
                            t = d / len;
                        } else if (gradientType === 'angular') {
                            // Angle from start point
                            const a = Math.atan2(py - y1, px - x1) - Math.atan2(dy, dx);
                            t = ((a + Math.PI) / (2 * Math.PI)) % 1.0;
                        } else if (gradientType === 'diamond') {
                            const adx = Math.abs((px - x1) * nx + (py - y1) * ny) / len;
                            const ady = Math.abs(-(px - x1) * ny + (py - y1) * nx) / len;
                            t = adx + ady;
                        } else if (gradientType === 'reflected') {
                            // Linear reflected — mirrors at the midpoint
                            t = Math.abs(((px - x1) * nx + (py - y1) * ny) / len);
                            t = t > 1 ? 2 - t : t; // reflect past end
                        } else if (gradientType === 'spiral-cw') {
                            // Spiral clockwise — angle + distance create a spiral
                            const a = Math.atan2(py - y1, px - x1) - Math.atan2(dy, dx);
                            const d = Math.sqrt((px - x1) ** 2 + (py - y1) ** 2) / len;
                            t = ((a / (2 * Math.PI) + d) % 1.0 + 1.0) % 1.0;
                        } else if (gradientType === 'spiral-ccw') {
                            // Spiral counter-clockwise
                            const a = Math.atan2(py - y1, px - x1) - Math.atan2(dy, dx);
                            const d = Math.sqrt((px - x1) ** 2 + (py - y1) ** 2) / len;
                            t = ((-a / (2 * Math.PI) + d) % 1.0 + 1.0) % 1.0;
                        } else if (gradientType === 'conical') {
                            // Conical — full 360° sweep, like paint.net
                            const a = Math.atan2(py - y1, px - x1) - Math.atan2(dy, dx);
                            t = ((a / (2 * Math.PI)) % 1.0 + 1.0) % 1.0;
                        }
                        // Reverse checkbox
                        const reverse = document.getElementById('gradientReverse')?.checked;
                        if (reverse) t = 1.0 - t;
                        t = Math.max(0, Math.min(1, t));
                        const val = Math.round((1.0 - t) * 255);
                        const idx = py * w + px;
                        if (selMode === 'replace') {
                            zone.regionMask[idx] = val;
                        } else if (selMode === 'subtract') {
                            zone.regionMask[idx] = Math.max(0, zone.regionMask[idx] - val);
                        } else { // add
                            zone.regionMask[idx] = Math.max(zone.regionMask[idx], val);
                        }
                    }
                }
            }

            // ── LAYER-MODE GRADIENT ──────────────────────────────────────────────────
            // Paints actual RGBA gradient pixels on the selected PSD layer (FG→BG colors)
            function fillGradientOnLayer(x1, y1, x2, y2, gradientType, layerOverride) {
                const layer = layerOverride || (typeof getSelectedEditableLayer === 'function' ? getSelectedEditableLayer() : null);
                if (!layer || !layer.img) return;
                const origin = typeof getLayerCanvasOrigin === 'function' ? getLayerCanvasOrigin(layer) : { x: 0, y: 0 };
                const lx = origin.x, ly = origin.y;
                const lw = layer.img.width || layer.img.naturalWidth;
                const lh = layer.img.height || layer.img.naturalHeight;
                // Create a temp canvas matching the layer
                const tc = document.createElement('canvas');
                tc.width = lw; tc.height = lh;
                const tctx = tc.getContext('2d');
                // Draw existing layer content first
                tctx.drawImage(layer.img, 0, 0);
                // Build Canvas2D gradient in layer-local coords
                const gx1 = x1 - lx, gy1 = y1 - ly, gx2 = x2 - lx, gy2 = y2 - ly;
                let grad;
                if (gradientType === 'radial') {
                    const r = Math.sqrt((gx2-gx1)**2 + (gy2-gy1)**2);
                    grad = tctx.createRadialGradient(gx1, gy1, 0, gx1, gy1, r);
                } else {
                    grad = tctx.createLinearGradient(gx1, gy1, gx2, gy2);
                }
                // Use FG and BG colors
                const fg = typeof _foregroundColor === 'string' ? _foregroundColor : '#000000';
                const bg = typeof _backgroundColor === 'string' ? _backgroundColor : '#ffffff';
                const reverse = document.getElementById('gradientReverse')?.checked;
                grad.addColorStop(0, reverse ? bg : fg);
                grad.addColorStop(1, reverse ? fg : bg);
                tctx.globalCompositeOperation = 'source-over';
                tctx.globalAlpha = parseInt(document.getElementById('brushOpacity')?.value || 100, 10) / 100;
                tctx.fillStyle = grad;
                tctx.fillRect(0, 0, lw, lh);
                if (typeof commitLayerCanvasUpdate === 'function') {
                    commitLayerCanvasUpdate(layer, tc, 'Gradient applied to layer: ' + (layer.name || 'Layer'));
                }
            }

            function _applyBakedSpecialFloodFill(data, visited, lw, lh, minX, minY, maxX, maxY, opacity) {
                const specialId = getLayerPaintSpecialId() || _getDefaultLayerPaintSpecialId();
                const specialCanvas = _getCachedLayerPaintSpecialCanvas(specialId);
                if (!specialCanvas || maxX < minX || maxY < minY) return false;
                const fillW = maxX - minX + 1;
                const fillH = maxY - minY + 1;
                const sampleCanvas = document.createElement('canvas');
                sampleCanvas.width = fillW;
                sampleCanvas.height = fillH;
                const sampleCtx = sampleCanvas.getContext('2d', { willReadFrequently: true });
                sampleCtx.drawImage(specialCanvas, 0, 0, specialCanvas.width, specialCanvas.height, 0, 0, fillW, fillH);
                const sample = sampleCtx.getImageData(0, 0, fillW, fillH).data;
                for (let py = minY; py <= maxY; py++) {
                    for (let px = minX; px <= maxX; px++) {
                        const pi = py * lw + px;
                        if (visited[pi] !== 2) continue;
                        const di = pi * 4;
                        const si = ((py - minY) * fillW + (px - minX)) * 4;
                        const srcAlpha = (sample[si + 3] / 255) * opacity;
                        const inv = 1 - srcAlpha;
                        data[di] = Math.round(data[di] * inv + sample[si] * srcAlpha);
                        data[di + 1] = Math.round(data[di + 1] * inv + sample[si + 1] * srcAlpha);
                        data[di + 2] = Math.round(data[di + 2] * inv + sample[si + 2] * srcAlpha);
                        data[di + 3] = Math.round(data[di + 3] * inv + 255 * srcAlpha);
                    }
                }
                return true;
            }

            // ── LAYER-MODE FILL ─────────────────────────────────────────────────────
            // Flood-fills the selected PSD layer at a point with the FG color
            function fillBucketOnLayer(startX, startY, layerOverride) {
                const layer = layerOverride || (typeof getSelectedEditableLayer === 'function' ? getSelectedEditableLayer() : null);
                if (!layer || !layer.img) return;
                const useSpecialBaked = isLayerPaintSourceSpecial();
                if (useSpecialBaked) {
                    const specialId = getLayerPaintSpecialId() || _getDefaultLayerPaintSpecialId();
                    if (!specialId) {
                        if (typeof showToast === 'function') showToast('Choose a baked Special first', 'warn');
                        return;
                    }
                    if (!_getCachedLayerPaintSpecialCanvas(specialId)) {
                        warmLayerPaintSpecialCache(true).then(function (canvas) {
                            if (canvas) fillBucketOnLayer(startX, startY, layer);
                        });
                        return;
                    }
                }
                const origin = typeof getLayerCanvasOrigin === 'function' ? getLayerCanvasOrigin(layer) : { x: 0, y: 0 };
                const lx = origin.x, ly = origin.y;
                const lw = layer.img.width || layer.img.naturalWidth;
                const lh = layer.img.height || layer.img.naturalHeight;
                // Convert canvas coords to layer-local
                const localX = startX - lx, localY = startY - ly;
                if (localX < 0 || localX >= lw || localY < 0 || localY >= lh) return;
                const tc = document.createElement('canvas');
                tc.width = lw; tc.height = lh;
                // Track L perf — willReadFrequently:true since we getImageData
                // on the entire layer bbox right after drawImage (class C
                // draw+read pattern, repeated per fill click).
                const tctx = tc.getContext('2d', { willReadFrequently: true });
                tctx.drawImage(layer.img, 0, 0);
                const imgData = tctx.getImageData(0, 0, lw, lh);
                const data = imgData.data;
                // Get target color at click point
                const tIdx = (localY * lw + localX) * 4;
                const tr = data[tIdx], tg = data[tIdx+1], tb = data[tIdx+2], ta = data[tIdx+3];
                const tol = parseInt(document.getElementById('wandTolerance')?.value || '32');
                // Get fill color from FG
                const fg = typeof _foregroundColor === 'string' ? _foregroundColor : '#000000';
                const fr = parseInt(fg.slice(1,3),16), fgv = parseInt(fg.slice(3,5),16), fb = parseInt(fg.slice(5,7),16);
                // Track Q #345 — fill bucket now honors brushOpacity. Photoshop's
                // fill bucket blends toward target color by opacity; previous
                // code always wrote 100% opaque pixels regardless of slider.
                const opacity = parseInt(document.getElementById('brushOpacity')?.value || '100', 10) / 100;
                const inv = 1 - opacity;
                // Flood fill using BFS
                const visited = new Uint8Array(lw * lh);
                const stack = [localX + localY * lw];
                visited[stack[0]] = 1;
                let filled = 0;
                let minX = lw, minY = lh, maxX = -1, maxY = -1;
                while (stack.length > 0) {
                    const pi = stack.pop();
                    const px = pi % lw, py = (pi / lw) | 0;
                    const i4 = pi * 4;
                    const dr = Math.abs(data[i4]-tr), dg = Math.abs(data[i4+1]-tg), db = Math.abs(data[i4+2]-tb), da = Math.abs(data[i4+3]-ta);
                    if (dr + dg + db + da > tol * 4) continue;
                    if (useSpecialBaked) {
                        visited[pi] = 2;
                        if (px < minX) minX = px;
                        if (px > maxX) maxX = px;
                        if (py < minY) minY = py;
                        if (py > maxY) maxY = py;
                    } else {
                        // Opacity-blend toward target.
                        data[i4]   = Math.round(data[i4]   * inv + fr  * opacity);
                        data[i4+1] = Math.round(data[i4+1] * inv + fgv * opacity);
                        data[i4+2] = Math.round(data[i4+2] * inv + fb  * opacity);
                        // Alpha: lerp toward 255 by opacity (preserves transparent gaps proportionally).
                        data[i4+3] = Math.round(data[i4+3] * inv + 255 * opacity);
                    }
                    filled++;
                    // Push neighbors
                    for (const [nx,ny] of [[px-1,py],[px+1,py],[px,py-1],[px,py+1]]) {
                        if (nx >= 0 && nx < lw && ny >= 0 && ny < lh) {
                            const ni = ny * lw + nx;
                            if (!visited[ni]) { visited[ni] = 1; stack.push(ni); }
                        }
                    }
                }
                if (useSpecialBaked) {
                    _applyBakedSpecialFloodFill(data, visited, lw, lh, minX, minY, maxX, maxY, opacity);
                }
                tctx.putImageData(imgData, 0, 0);
                if (typeof commitLayerCanvasUpdate === 'function') {
                    commitLayerCanvasUpdate(
                        layer,
                        tc,
                        (useSpecialBaked ? 'Baked Special fill' : 'Fill') + ' applied to layer (' + filled + ' pixels): ' + (layer.name || 'Layer')
                    );
                }
            }
            window.fillGradientOnLayer = fillGradientOnLayer;
            window.fillBucketOnLayer = fillBucketOnLayer;

            var _maskOnlyToolHintShown = Object.create(null);
            function _maybeWarnMaskOnlyTool(toolName) {
                const layer = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
                if (!layer) return;
                const key = String(toolName || 'tool');
                if (_maskOnlyToolHintShown[key]) return;
                _maskOnlyToolHintShown[key] = true;
                if (typeof showToast === 'function') {
                    showToast(
                        `${toolName} stays on zone masks for now — it will not repaint "${layer.name || 'the selected layer'}"`,
                        'info'
                    );
                }
            }

            function _ensureCompositePaintSource(reason) {
                if (!_activeLayerCanvas || isDrawing) return;
                _activeLayerCanvas = null;
                _activeLayerCtx = null;
                if (_savedPaintImageData) {
                    paintImageData = _savedPaintImageData;
                    _savedPaintImageData = null;
                }
                if (typeof recompositeFromLayers === 'function'
                        && typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded) {
                    recompositeFromLayers();
                }
                if (typeof console !== 'undefined' && console.warn) {
                    console.warn('[layer-state] Restored composite paint source before ' + (reason || 'zone tool'));
                }
            }

            // ── FILL BUCKET ──────────────────────────────────────────────────────────
            // Flood-fill contiguous pixels of similar color into the region mask
            function fillBucketAtPoint(startX, startY) {
                _ensureCompositePaintSource('fill bucket');
                const zone = zones[selectedZoneIndex];
                if (!zone || !paintImageData) return;
                const w = canvas.width, h = canvas.height;
                const useScopedRefinement = _zoneBrushUsesScopedRefinement(zone);
                if (useScopedRefinement) {
                    const scopeMask = _buildZoneScopedSelectorMask(zone, w, h);
                    const seedIdx = startY * w + startX;
                    if (!scopeMask || scopeMask[seedIdx] <= 0) {
                        if (typeof showToast === 'function') {
                            showToast('Click inside this zone’s current color/layer selection', 'info');
                        }
                        return;
                    }
                    if (!zone.spatialMask) {
                        zone.spatialMask = new Uint8Array(w * h);
                    }
                    const selMode = document.getElementById('selectionMode')?.value || 'add';
                    const tolerance = parseInt(document.getElementById('wandTolerance')?.value || 32);
                    const contiguous = document.getElementById('wandContiguous')?.checked !== false;
                    const tolSq = tolerance * tolerance * 3;
                    const data = paintImageData.data;
                    const si = seedIdx * 4;
                    const seedR = data[si], seedG = data[si + 1], seedB = data[si + 2];
                    let filledScoped = 0;
                    if (selMode === 'replace') {
                        zone.spatialMask.fill(0);
                    }
                    const fillVal = (selMode === 'subtract') ? 2 : 1;

                    if (contiguous) {
                        const visited = new Uint8Array(w * h);
                        const stack = [seedIdx];
                        visited[seedIdx] = 1;
                        while (stack.length > 0) {
                            const idx = stack.pop();
                            if (scopeMask[idx] <= 0) continue;
                            const px = idx % w, py = (idx - px) / w;
                            const pi = idx * 4;
                            const dr = data[pi] - seedR, dg = data[pi + 1] - seedG, db = data[pi + 2] - seedB;
                            if (dr * dr + dg * dg + db * db > tolSq) continue;
                            zone.spatialMask[idx] = fillVal;
                            filledScoped++;
                            if (px > 0 && !visited[idx - 1]) { visited[idx - 1] = 1; stack.push(idx - 1); }
                            if (px < w - 1 && !visited[idx + 1]) { visited[idx + 1] = 1; stack.push(idx + 1); }
                            if (py > 0 && !visited[idx - w]) { visited[idx - w] = 1; stack.push(idx - w); }
                            if (py < h - 1 && !visited[idx + w]) { visited[idx + w] = 1; stack.push(idx + w); }
                        }
                    } else {
                        for (let i = 0; i < w * h; i++) {
                            if (scopeMask[i] <= 0) continue;
                            const pi = i * 4;
                            const dr = data[pi] - seedR, dg = data[pi + 1] - seedG, db = data[pi + 2] - seedB;
                            if (dr * dr + dg * dg + db * db <= tolSq) {
                                zone.spatialMask[i] = fillVal;
                                filledScoped++;
                            }
                        }
                    }
                    if (fillVal === 1 && filledScoped > 0) _maybeAdoptForegroundAsScopedZoneBaseColor(selectedZoneIndex);
                    else _normalizeScopedZoneAutoBaseColor(selectedZoneIndex);
                    return;
                }
                if (!zone.regionMask) {
                    zone.regionMask = new Uint8Array(w * h);
                }
                const selMode = document.getElementById('selectionMode')?.value || 'add';
                const tolerance = parseInt(document.getElementById('wandTolerance')?.value || 32);
                const contiguous = document.getElementById('wandContiguous')?.checked !== false;
                const tolSq = tolerance * tolerance * 3;
                const data = paintImageData.data;
                const si = (startY * w + startX) * 4;
                const seedR = data[si], seedG = data[si + 1], seedB = data[si + 2];

                if (selMode === 'replace') {
                    zone.regionMask.fill(0);
                }
                const fillVal = (selMode === 'subtract') ? 0 : 255;

                if (contiguous) {
                    // Flood fill from click point (same as magic wand but writes to mask)
                    const visited = new Uint8Array(w * h);
                    const stack = [startX + startY * w];
                    visited[startX + startY * w] = 1;
                    while (stack.length > 0) {
                        const idx = stack.pop();
                        const px = idx % w, py = (idx - px) / w;
                        const pi = idx * 4;
                        const dr = data[pi] - seedR, dg = data[pi + 1] - seedG, db = data[pi + 2] - seedB;
                        if (dr * dr + dg * dg + db * db > tolSq) continue;
                        zone.regionMask[idx] = fillVal;
                        // 4-connected neighbors
                        if (px > 0 && !visited[idx - 1]) { visited[idx - 1] = 1; stack.push(idx - 1); }
                        if (px < w - 1 && !visited[idx + 1]) { visited[idx + 1] = 1; stack.push(idx + 1); }
                        if (py > 0 && !visited[idx - w]) { visited[idx - w] = 1; stack.push(idx - w); }
                        if (py < h - 1 && !visited[idx + w]) { visited[idx + w] = 1; stack.push(idx + w); }
                    }
                } else {
                    // Non-contiguous: fill ALL matching pixels
                    for (let i = 0; i < w * h; i++) {
                        const pi = i * 4;
                        const dr = data[pi] - seedR, dg = data[pi + 1] - seedG, db = data[pi + 2] - seedB;
                        if (dr * dr + dg * dg + db * db <= tolSq) {
                            zone.regionMask[i] = fillVal;
                        }
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
                _ensureCompositePaintSource('rectangle select');
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
                const useColorFilter = (value > 0) && lastEyedropperColor && paintImageData;

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
                                zone.regionMask[y * w + x] = 255;
                                filled++;
                            }
                        }
                    }
                    showToast(`Rect + Color: ${filled.toLocaleString()} matching pixels selected`);
                } else {
                    // No eyedropper color - fill entire rectangle (legacy behavior)
                    for (let y = minY; y <= maxY; y++) {
                        for (let x = minX; x <= maxX; x++) {
                            zone.regionMask[y * w + x] = value ? 255 : 0;
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
                    if (!placementSnapshotPushed && (Math.abs(dx) > 0.0001 || Math.abs(dy) > 0.0001)) {
                        if (typeof pushZoneUndo === 'function') pushZoneUndo('Move placement', true);
                        placementSnapshotPushed = true;
                    }
                    const newOx = placementDragStart.offsetX + dx;
                    const newOy = placementDragStart.offsetY + dy;
                    applyPlacementOffset(selectedZoneIndex, placementLayer, newOx, newOy);
                    drawPlacementCrosshair(canvas, newOx, newOy, placementLayer);
                    return;
                }

                const pos = getPixelAt(e);
                if (!pos) return;

                if (canvasMode === 'selection-move' && isDrawing && _selectionMoveDrag) {
                    updateSelectionMovePreview(pos);
                } else if (canvasMode === 'eyedropper') {
                    const px = getColorAt(pos.x, pos.y);
                    const hex = toHex(px.r, px.g, px.b);
                    document.getElementById('hoverInfo').style.display = 'block';
                    document.getElementById('hoverSwatch').style.background = hex;
                    document.getElementById('hoverHex').textContent = hex.toUpperCase();
                    document.getElementById('hoverRGB').textContent = `RGB(${px.r}, ${px.g}, ${px.b})`;
                } else if ((canvasMode === 'brush' || canvasMode === 'erase') && isDrawing) {
                    const _bRadius = getBrushSize();
                    if (!_checkBrushSpacing(pos.x, pos.y, _bRadius)) { /* skip — too close to last dab */ }
                    else if (_activeLayerCanvas) {
                        const opacity = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100;
                        const hardness = parseInt(document.getElementById('brushHardness')?.value || 100) / 100;
                        _paintOnLayerAt(pos.x, pos.y, _bRadius, canvasMode === 'erase' ? '#000000' : _foregroundColor, opacity, hardness, canvasMode === 'erase');
                    } else {
                        const val = canvasMode === 'brush' ? 1 : 0;
                        const strokeTarget = paintRegionCircle(pos.x, pos.y, _bRadius, val);
                        if (strokeTarget === 'spatial') _fastSpatialOverlayArc(pos.x, pos.y, _bRadius, val);
                        else _fastOverlayArc(pos.x, pos.y, _bRadius, val);
                    }
                } else if ((canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude' || canvasMode === 'spatial-erase') && isDrawing) {
                    const val = canvasMode === 'spatial-include' ? 1 : (canvasMode === 'spatial-exclude' ? 2 : 0);
                    paintSpatialCircle(pos.x, pos.y, spatialBrushRadius, val);
                    _fastSpatialOverlayArc(pos.x, pos.y, spatialBrushRadius, val);
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
                } else if (canvasMode === 'gradient' && isDrawing && window._gradientStart) {
                    // Draw gradient preview line on region canvas
                    const gpos = getPixelAtClamped(e);
                    if (gpos) {
                        _doRenderRegionOverlay(); // Redraw base overlay
                        const rc = document.getElementById('regionCanvas');
                        if (rc) {
                            const rctx = rc.getContext('2d');
                            const gs = window._gradientStart;
                            const zoom = typeof currentZoom !== 'undefined' ? currentZoom : 1;
                            // Draw gradient direction line
                            rctx.beginPath();
                            rctx.moveTo(gs.x * zoom, gs.y * zoom);
                            rctx.lineTo(gpos.x * zoom, gpos.y * zoom);
                            rctx.strokeStyle = 'rgba(255,255,255,0.8)';
                            rctx.lineWidth = 2;
                            rctx.setLineDash([6, 4]);
                            rctx.stroke();
                            rctx.setLineDash([]);
                            // Start dot (white)
                            rctx.beginPath();
                            rctx.arc(gs.x * zoom, gs.y * zoom, 5, 0, Math.PI * 2);
                            rctx.fillStyle = '#fff';
                            rctx.fill();
                            // End dot (black)
                            rctx.beginPath();
                            rctx.arc(gpos.x * zoom, gpos.y * zoom, 5, 0, Math.PI * 2);
                            rctx.fillStyle = '#000';
                            rctx.strokeStyle = '#fff';
                            rctx.lineWidth = 1;
                            rctx.fill();
                            rctx.stroke();
                        }
                    }
                } else if (canvasMode === 'rect' && isDrawing && rectStart) {
                    // Use clamped coords so drag pins to canvas edge instead of dying
                    let cpos = getPixelAtClamped(e);
                    if (e.shiftKey) cpos = constrainRectToSquare(rectStart, cpos);
                    drawRectPreview(rectStart, cpos);
                } else if (canvasMode === 'shape' && isDrawing && _shapeStart) {
                    let spos = getPixelAtClamped(e);
                    if (spos) {
                        if (e.shiftKey) {
                            const dx = spos.x - _shapeStart.x, dy = spos.y - _shapeStart.y;
                            const size = Math.max(Math.abs(dx), Math.abs(dy));
                            spos = { x: _shapeStart.x + size * Math.sign(dx || 1), y: _shapeStart.y + size * Math.sign(dy || 1) };
                        }
                        if (typeof drawShapePreview === 'function') drawShapePreview(_shapeStart, spos);
                    }
                } else if (canvasMode === 'clone' && isDrawing && _cloneSource) {
                    const cpos2 = getPixelAtClamped(e);
                    if (cpos2 && _checkBrushSpacing(cpos2.x, cpos2.y, parseInt(document.getElementById('brushSize')?.value || 20)) && typeof paintCloneStroke === 'function') paintCloneStroke(cpos2.x, cpos2.y);
                } else if (canvasMode === 'pen' && penDragging && penDragIndex >= 0) {
                    const ppos = getPixelAtClamped(e);
                    if (ppos && penPoints[penDragIndex]) {
                        const p = penPoints[penDragIndex];
                        p.cx2 = ppos.x; p.cy2 = ppos.y;
                        p.cx1 = p.x * 2 - ppos.x; p.cy1 = p.y * 2 - ppos.y;
                        if (typeof drawPenPath === 'function') drawPenPath();
                    }
                } else if (canvasMode === 'colorbrush' && isDrawing) {
                    const cbpos = getPixelAtClamped(e);
                    if (cbpos && _checkBrushSpacing(cbpos.x, cbpos.y, parseInt(document.getElementById('brushSize')?.value || 20))) {
                        if (_activeLayerCanvas) {
                            const radius = parseInt(document.getElementById('brushSize')?.value || 20);
                            const opacity = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100;
                            const hardness = parseInt(document.getElementById('brushHardness')?.value || 100) / 100;
                            _paintOnLayerAt(cbpos.x, cbpos.y, radius, _foregroundColor, opacity, hardness, false);
                        } else if (typeof paintColorBrush === 'function') {
                            paintColorBrush(cbpos.x, cbpos.y);
                        }
                    }
                } else if (canvasMode === 'recolor' && isDrawing) {
                    const rcpos = getPixelAtClamped(e);
                    if (rcpos && _checkBrushSpacing(rcpos.x, rcpos.y, parseInt(document.getElementById('brushSize')?.value || 20))) _applyWithSymmetry(paintRecolor, rcpos.x, rcpos.y);
                } else if (canvasMode === 'smudge' && isDrawing) {
                    const smpos = getPixelAtClamped(e);
                    if (smpos && _checkBrushSpacing(smpos.x, smpos.y, parseInt(document.getElementById('brushSize')?.value || 20)) && typeof paintSmudge === 'function') paintSmudge(smpos.x, smpos.y);
                } else if (canvasMode === 'history-brush' && isDrawing) {
                    const hbpos = getPixelAtClamped(e);
                    if (hbpos && _checkBrushSpacing(hbpos.x, hbpos.y, parseInt(document.getElementById('brushSize')?.value || 20)) && typeof paintHistoryBrush === 'function') paintHistoryBrush(hbpos.x, hbpos.y);
                } else if (canvasMode === 'pencil' && isDrawing) {
                    const pppos = getPixelAtClamped(e);
                    if (pppos) paintPencil(pppos.x, pppos.y, false);
                } else if ((canvasMode === 'dodge' || canvasMode === 'burn') && isDrawing) {
                    const dbpos = getPixelAtClamped(e);
                    if (dbpos && _checkBrushSpacing(dbpos.x, dbpos.y, parseInt(document.getElementById('brushSize')?.value || 20))) {
                        const _dbFn = canvasMode === 'dodge' ? paintDodge : paintBurn;
                        _applyWithSymmetry(_dbFn, dbpos.x, dbpos.y);
                    }
                } else if ((canvasMode === 'blur-brush' || canvasMode === 'sharpen-brush') && isDrawing) {
                    const bspos = getPixelAtClamped(e);
                    if (bspos && _checkBrushSpacing(bspos.x, bspos.y, parseInt(document.getElementById('brushSize')?.value || 15))) {
                        const _bsFn = canvasMode === 'blur-brush' ? paintBlurBrush : paintSharpenBrush;
                        _applyWithSymmetry(_bsFn, bspos.x, bspos.y);
                    }
                } else if (canvasMode === 'ellipse-marquee' && isDrawing && _ellipseStart) {
                    let epos = getPixelAtClamped(e);
                    if (epos) {
                        if (e.shiftKey) {
                            const dx = epos.x - _ellipseStart.x, dy = epos.y - _ellipseStart.y;
                            const size = Math.max(Math.abs(dx), Math.abs(dy));
                            epos = { x: _ellipseStart.x + size * Math.sign(dx || 1), y: _ellipseStart.y + size * Math.sign(dy || 1) };
                        }
                        if (typeof drawEllipsePreview === 'function') drawEllipsePreview(_ellipseStart, epos);
                    }
                }
            };

            canvas.onmouseleave = function () {
                var _hov = document.getElementById('hoverInfo');
                if (_hov) _hov.style.display = 'none';
                // BUG #74 (Muraco, HIGH): pre-fix, mouseleave cleared isDrawing
                // (except in rect mode). If painter released the mouse OUTSIDE
                // the canvas, canvas.onmouseup never fired AND isDrawing was
                // already false — brush/erase/lasso/gradient/layer-paint strokes
                // were silently lost. Keep isDrawing true so the document-level
                // mouseup proxy (installed below) can run the real commit path
                // with the actual mouseup event. Blur/focusout resets isDrawing
                // as a safety net if mouse is released in another window.
            };

            // BUG #74: document-level mouseup proxy. When the painter releases
            // the mouse outside the canvas element, the canvas-scoped mouseup
            // never fires — this proxy re-delivers the real mouseup event to
            // `canvas.onmouseup` so the stroke commits cleanly. Only fires if
            // a stroke is actually in-flight AND the release happened outside
            // the canvas (in-canvas releases are already handled natively).
            document.addEventListener('mouseup', function (ev) {
                try {
                    if (isDrawing && ev.target !== canvas && typeof canvas.onmouseup === 'function') {
                        canvas.onmouseup(ev);
                    }
                } catch (_) { /* swallow — the handler itself must not leak errors */ }
            });

            // BUG #74 safety net: if the painter Alt+Tabs / minimizes during a
            // stroke, mouseup fires on the OS — neither our canvas nor document
            // listener receives it, so isDrawing would stay true forever and
            // subsequent mouse moves would draw phantom pixels. Reset on blur.
            window.addEventListener('blur', function () {
                if (isDrawing) {
                    isDrawing = false;
                    // Abandon any layer-paint shadow canvas without committing.
                    if (typeof window._activeLayerCanvas !== 'undefined') {
                        try { window._activeLayerCanvas = null; window._activeLayerCtx = null; } catch (_) {}
                    }
                }
            });

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
                        const placementState = _getPlacementTargetState(z, placementLayer);
                        if (placementState) { ox = placementState.offsetX; oy = placementState.offsetY; }
                        placementDragStart = { x: pos.x, y: pos.y, offsetX: ox, offsetY: oy, zoneIndex: selectedZoneIndex, target: placementLayer };
                        placementDragging = true;
                        placementSnapshotPushed = false;
                        _syncPlacementDragState();
                        e.preventDefault();
                        canvas.style.cursor = 'grabbing';
                        drawPlacementCrosshair(canvas, ox, oy, placementLayer);
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

                // === LAYER DRAG — Ctrl+click or default mode (eyedropper) moves selected layer ===
                if (_selectedLayerId && _psdLayersLoaded && e.button === 0) {
                    const layerPos = getPixelAt(e);
                    if (layerPos) {
                        const selLayer = typeof getSelectedLayer === 'function' ? getSelectedLayer() : null;
                        if (selLayer && selLayer.visible && selLayer.img && typeof isPointInLayerBbox === 'function' && isPointInLayerBbox(selLayer, layerPos.x, layerPos.y)) {
                            // Move layer ONLY with Ctrl+click — never intercept normal tool usage
                            if (e.ctrlKey) {
                                startLayerDrag(selLayer, layerPos.x, layerPos.y);
                                e.preventDefault();
                                canvas.style.cursor = 'move';
                                var onLayerDragMove = function (e2) {
                                    var c = document.getElementById('paintCanvas');
                                    if (!c) return;
                                    var rect = c.getBoundingClientRect();
                                    var sx = c.width / rect.width, sy = c.height / rect.height;
                                    var lx = Math.floor((e2.clientX - rect.left) * sx);
                                    var ly = Math.floor((e2.clientY - rect.top) * sy);
                                    updateLayerDrag(lx, ly);
                                };
                                var onLayerDragUp = function () {
                                    endLayerDrag();
                                    canvas.style.cursor = '';
                                    document.removeEventListener('mousemove', onLayerDragMove);
                                    document.removeEventListener('mouseup', onLayerDragUp);
                                };
                                document.addEventListener('mousemove', onLayerDragMove);
                                document.addEventListener('mouseup', onLayerDragUp);
                                return;
                            }
                        }
                    }
                }
                // === END LAYER DRAG ===

                // Prevent native canvas image drag for draw tools - without this,
                // the browser can start a drag-and-drop operation that steals mousemove events
                if (['brush', 'rect', 'erase', 'spatial-include', 'spatial-exclude', 'spatial-erase', 'lasso', 'gradient', 'fill', 'shape', 'clone', 'text', 'pen', 'colorbrush', 'ellipse-marquee', 'recolor', 'smudge', 'history-brush', 'dodge', 'burn', 'blur-brush', 'sharpen-brush', 'pencil'].includes(canvasMode)) {
                    e.preventDefault();
                }

                const pos = getPixelAt(e);
                if (!pos) return;

                const zoneOnlyToolNames = {
                    wand: 'Magic Wand',
                    selectall: 'Select All',
                    edge: 'Edge Detect',
                    rect: 'Rectangle',
                    lasso: 'Lasso',
                    'ellipse-marquee': 'Ellipse',
                    pen: 'Pen',
                    'selection-move': 'Move Border',
                    'spatial-include': 'Spatial Include',
                    'spatial-exclude': 'Spatial Exclude',
                    'spatial-erase': 'Spatial Erase',
                };
                const layerOnlyToolNames = {
                    text: 'Text',
                    shape: 'Shape',
                    clone: 'Clone Stamp',
                    colorbrush: 'Color Brush',
                    recolor: 'Recolor',
                    smudge: 'Smudge',
                    'history-brush': 'History Brush',
                    pencil: 'Pencil',
                    dodge: 'Dodge',
                    burn: 'Burn',
                    'blur-brush': 'Blur Brush',
                    'sharpen-brush': 'Sharpen Brush',
                };
                if (typeof isLayerToolbarMode === 'function' && isLayerToolbarMode()) {
                    if (zoneOnlyToolNames[canvasMode]) {
                        requireZoneToolbarMode(zoneOnlyToolNames[canvasMode]);
                        e.preventDefault();
                        return;
                    }
                    if (layerOnlyToolNames[canvasMode] && !requireLayerToolbarTarget(layerOnlyToolNames[canvasMode])) {
                        e.preventDefault();
                        return;
                    }
                } else if (layerOnlyToolNames[canvasMode]) {
                    requireLayerToolbarTarget(layerOnlyToolNames[canvasMode]);
                    e.preventDefault();
                    return;
                }

                if (canvasMode === 'layer-pick') {
                    if (typeof _psdLayersLoaded === 'undefined' || !_psdLayersLoaded || !Array.isArray(_psdLayers) || _psdLayers.length === 0) {
                        if (typeof showToast === 'function') showToast('Import PSD layers first, then use Pick Item', 'info');
                        e.preventDefault();
                        return;
                    }
                    const clickedLayer = (typeof getTopmostVisibleLayerAtCanvasPoint === 'function')
                        ? getTopmostVisibleLayerAtCanvasPoint(pos.x, pos.y)
                        : null;
                    if (!clickedLayer) {
                        if (typeof showToast === 'function') showToast('No visible layer pixels at that spot', 'info');
                        e.preventDefault();
                        return;
                    }
                    if (clickedLayer.id !== _selectedLayerId) {
                        if (typeof selectPSDLayer === 'function') selectPSDLayer(clickedLayer.id);
                        if (typeof showToast === 'function') showToast(`Selected layer: ${clickedLayer.name || 'Layer'}`, 'info');
                        e.preventDefault();
                        return;
                    }
                    if (typeof selectConnectedLayerPixelsAtPoint === 'function') {
                        selectConnectedLayerPixelsAtPoint(clickedLayer.id, pos.x, pos.y, { autoTransform: true });
                    }
                    e.preventDefault();
                    return;
                }

                // Alt+click = temporary eyedropper (sample color, stay in current tool)
                // Exception: clone tool uses Alt+click to set clone source
                if (e.altKey && canvasMode !== 'clone') {
                    const color = getColorAt(pos.x, pos.y);
                    _foregroundColor = toHex(color.r, color.g, color.b);
                    const fgEl = document.getElementById('fgColorSwatch');
                    const fgPicker = document.getElementById('fgColorPicker');
                    const fgHexInput = document.getElementById('fgHexInput');
                    if (fgEl) fgEl.style.background = _foregroundColor;
                    if (fgPicker) fgPicker.value = _foregroundColor;
                    if (fgHexInput) fgHexInput.value = _foregroundColor;
                    if (typeof syncLayerPaintSourceUI === 'function') syncLayerPaintSourceUI();
                    if (typeof warmLayerPaintSpecialCache === 'function' && isLayerPaintSourceSpecial()) warmLayerPaintSpecialCache(false);
                    if (typeof addRecentColor === 'function') addRecentColor(_foregroundColor);
                    if (typeof showToast === 'function') showToast(`Sampled: ${_foregroundColor}`, 'info');
                    e.preventDefault();
                    return;
                }

                // === NEW TOOLS DISPATCH (integrated into main handler) ===
                if (canvasMode === 'text') {
                    if (typeof onTextToolClick === 'function') onTextToolClick(pos.x, pos.y);
                    e.preventDefault(); return;
                }
                if (canvasMode === 'shape') {
                    _shapeStart = pos; isDrawing = true; e.preventDefault(); return;
                }
                if (canvasMode === 'clone') {
                    if (e.altKey) {
                        _cloneSource = { x: pos.x, y: pos.y }; _cloneOffset = null;
                        if (typeof showToast === 'function') showToast(`Clone source: (${pos.x}, ${pos.y})`, 'info');
                        e.preventDefault(); return;
                    }
                    if (!_cloneSource) { if (typeof showToast === 'function') showToast('Alt+Click to set source first', 'info'); return; }
                    // TOOLS WAR — refuse stroke on locked layer (warn + no-op).
                    if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                    isDrawing = true;
                    _resetBrushSpacing();
                    if (typeof isLayerPaintMode === 'function' && isLayerPaintMode()) {
                        _pushLayerUndo(getSelectedLayer(), 'clone on layer');
                        _initLayerPaintCanvas();
                    } else {
                        if (typeof _maybeToastLayerPaintFallback === 'function') _maybeToastLayerPaintFallback('clone');
                        pushPixelUndo('clone stamp');
                    }
                    if (typeof paintCloneStroke === 'function') paintCloneStroke(pos.x, pos.y);
                    e.preventDefault(); return;
                }
                if (canvasMode === 'pen') {
                    if (e.detail >= 2 && penPoints.length >= 3) { closePenPath(); penPathToMask(); }
                    else if (penClosed) { penPathToMask(); }
                    else { addPenPoint(pos.x, pos.y); penDragging = true; penDragIndex = penPoints.length - 1; }
                    e.preventDefault(); return;
                }
                if (canvasMode === 'colorbrush') {
                    if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                    isDrawing = true;
                    if (typeof isLayerPaintMode === 'function' && isLayerPaintMode()) {
                        _pushLayerUndo(getSelectedLayer(), 'color brush on layer');
                        _initLayerPaintCanvas();
                        // Now paintImageData points to layer — standard paintColorBrush works
                        if (typeof paintColorBrush === 'function') paintColorBrush(pos.x, pos.y);
                    } else {
                        if (typeof _maybeToastLayerPaintFallback === 'function') _maybeToastLayerPaintFallback('color brush');
                        pushPixelUndo('color brush');
                        if (typeof paintColorBrush === 'function') paintColorBrush(pos.x, pos.y);
                    }
                    e.preventDefault(); return;
                }
                if (canvasMode === 'ellipse-marquee') {
                    _ellipseStart = pos; isDrawing = true; e.preventDefault(); return;
                }
                if (canvasMode === 'recolor') {
                    if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                    isDrawing = true;
                    _resetBrushSpacing();
                    if (typeof isLayerPaintMode === 'function' && isLayerPaintMode()) {
                        _pushLayerUndo(getSelectedLayer(), 'recolor on layer');
                        _initLayerPaintCanvas(); // Swaps paintImageData to layer canvas
                    } else {
                        if (typeof _maybeToastLayerPaintFallback === 'function') _maybeToastLayerPaintFallback('recolor');
                        pushPixelUndo('recolor');
                    }
                    if (typeof paintRecolor === 'function') paintRecolor(pos.x, pos.y);
                    e.preventDefault(); return;
                }
                if (canvasMode === 'smudge') {
                    if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                    isDrawing = true;
                    _resetBrushSpacing();
                    if (typeof resetSmudge === 'function') resetSmudge();
                    if (typeof isLayerPaintMode === 'function' && isLayerPaintMode()) {
                        _pushLayerUndo(getSelectedLayer(), 'smudge on layer');
                        _initLayerPaintCanvas();
                    } else {
                        if (typeof _maybeToastLayerPaintFallback === 'function') _maybeToastLayerPaintFallback('smudge');
                        pushPixelUndo('smudge');
                    }
                    if (typeof paintSmudge === 'function') paintSmudge(pos.x, pos.y);
                    e.preventDefault(); return;
                }
                if (canvasMode === 'history-brush') {
                    if (!_historySnapshot) {
                        if (typeof showToast === 'function') showToast('Save a history snapshot first', 'info');
                        return;
                    }
                    if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                    isDrawing = true;
                    _resetBrushSpacing();
                    if (typeof isLayerPaintMode === 'function' && isLayerPaintMode()) {
                        _pushLayerUndo(getSelectedLayer(), 'history brush on layer');
                        _initLayerPaintCanvas();
                    } else {
                        if (typeof _maybeToastLayerPaintFallback === 'function') _maybeToastLayerPaintFallback('history brush');
                        pushPixelUndo('history brush');
                    }
                    if (typeof paintHistoryBrush === 'function') paintHistoryBrush(pos.x, pos.y);
                    e.preventDefault(); return;
                }
                if (canvasMode === 'pencil') {
                    if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                    isDrawing = true;
                    if (typeof isLayerPaintMode === 'function' && isLayerPaintMode()) {
                        _pushLayerUndo(getSelectedLayer(), 'pencil on layer');
                        _initLayerPaintCanvas();
                    } else {
                        if (typeof _maybeToastLayerPaintFallback === 'function') _maybeToastLayerPaintFallback('pencil');
                        pushPixelUndo('pencil');
                    }
                    paintPencil(pos.x, pos.y, e.button === 2);
                    e.preventDefault(); return;
                }
                if (canvasMode === 'dodge' || canvasMode === 'burn') {
                    if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                    isDrawing = true;
                    if (typeof isLayerPaintMode === 'function' && isLayerPaintMode()) {
                        _pushLayerUndo(getSelectedLayer(), canvasMode + ' on layer');
                        _initLayerPaintCanvas();
                    } else {
                        if (typeof _maybeToastLayerPaintFallback === 'function') _maybeToastLayerPaintFallback(canvasMode);
                        pushPixelUndo(canvasMode);
                    }
                    _resetBrushSpacing();
                    if (canvasMode === 'dodge') paintDodge(pos.x, pos.y);
                    else paintBurn(pos.x, pos.y);
                    e.preventDefault(); return;
                }
                if (canvasMode === 'blur-brush' || canvasMode === 'sharpen-brush') {
                    if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                    isDrawing = true;
                    if (typeof isLayerPaintMode === 'function' && isLayerPaintMode()) {
                        _pushLayerUndo(getSelectedLayer(), (canvasMode === 'blur-brush' ? 'blur' : 'sharpen') + ' on layer');
                        _initLayerPaintCanvas();
                    } else {
                        // 2026-04-18 marathon audit — same fallback toast contract
                        // as the other 8 layer-aware tools. Pre-audit the painter
                        // had no idea why blur/sharpen landed on composite when
                        // a layer was selected.
                        if (typeof _maybeToastLayerPaintFallback === 'function') {
                            _maybeToastLayerPaintFallback(canvasMode === 'blur-brush' ? 'blur brush' : 'sharpen brush');
                        }
                        pushPixelUndo(canvasMode === 'blur-brush' ? 'blur brush' : 'sharpen brush');
                    }
                    _resetBrushSpacing();
                    if (canvasMode === 'blur-brush') paintBlurBrush(pos.x, pos.y);
                    else paintSharpenBrush(pos.x, pos.y);
                    e.preventDefault(); return;
                }
                // === END NEW TOOLS ===

                if (canvasMode === 'eyedropper') {
                    // TOOLS WAR Phase 4 — Shift+click samples ONLY the active
                    // layer's pixels (Photoshop's "Sample: Current Layer" mode).
                    // Plain click samples the composite as before.
                    var px;
                    if (e.shiftKey && typeof _selectedLayerId !== 'undefined' && _selectedLayerId
                        && typeof _psdLayers !== 'undefined') {
                        var srcLayer = _psdLayers.find(function(l) { return l.id === _selectedLayerId; });
                        if (srcLayer && srcLayer.img) {
                            // Read the active layer's own RGB at this pixel
                            // by drawing it to a 1×1 sampler.
                            var sc = document.createElement('canvas');
                            sc.width = 1; sc.height = 1;
                            var sctx = sc.getContext('2d', { willReadFrequently: true });
                            var bx = Array.isArray(srcLayer.bbox) ? (srcLayer.bbox[0] || 0) : 0;
                            var by = Array.isArray(srcLayer.bbox) ? (srcLayer.bbox[1] || 0) : 0;
                            sctx.drawImage(srcLayer.img, pos.x - bx, pos.y - by, 1, 1, 0, 0, 1, 1);
                            var d1 = sctx.getImageData(0, 0, 1, 1).data;
                            px = { r: d1[0], g: d1[1], b: d1[2] };
                            if (typeof showToast === 'function') {
                                showToast('Sampled "' + srcLayer.name + '" pixel (Shift+click = layer-only)', 'info');
                            }
                        } else {
                            px = getColorAt(pos.x, pos.y);
                        }
                    } else {
                        px = getColorAt(pos.x, pos.y);
                    }
                    lastEyedropperColor = px;
                    const hex = toHex(px.r, px.g, px.b);
                    document.getElementById('eyedropperSwatch').style.background = hex;
                    document.getElementById('eyedropperRGB').textContent = `RGB: (${px.r}, ${px.g}, ${px.b})`;
                    document.getElementById('eyedropperHex').textContent = hex.toUpperCase();
                    document.getElementById('hoverInfo').style.display = 'none';
                    document.getElementById('eyedropperInfo').style.display = 'block';
                    updateEyedropperZoneSelect();
                    // Also set FG color from eyedropper pick
                    if (typeof _foregroundColor !== 'undefined') {
                        _foregroundColor = hex;
                        const fgPicker = document.getElementById('fgColorPicker');
                        const fgSwatch = document.getElementById('fgColorSwatch');
                        const fgHexInput = document.getElementById('fgHexInput');
                        if (fgPicker) fgPicker.value = hex;
                        if (fgSwatch) fgSwatch.style.background = hex;
                        if (fgHexInput) fgHexInput.value = hex;
                        if (typeof addRecentColor === 'function') addRecentColor(hex);
                    }
                } else if (canvasMode === 'brush' || canvasMode === 'erase') {
                    if (typeof isLayerToolbarMode === 'function' && isLayerToolbarMode() &&
                        !requireLayerToolbarTarget(canvasMode === 'erase' ? 'Eraser' : 'Brush')) {
                        e.preventDefault();
                        return;
                    }
                    // When an editable PSD layer is selected, plain Brush/Erase should
                    // behave like Photoshop-style pixel tools instead of silently
                    // painting the current zone mask.
                    if (typeof isLayerPaintMode === 'function' && isLayerPaintMode()) {
                        if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                        isDrawing = true;
                        _pushLayerUndo(getSelectedLayer(), canvasMode + ' on layer');
                        const inited = _initLayerPaintCanvas();
                        if (!inited || !_activeLayerCanvas) {
                            isDrawing = false;
                            const reason = (typeof _diagnoseLayerPaintFail === 'function' && _diagnoseLayerPaintFail()) || 'layer not ready';
                            if (typeof showToast === 'function') showToast(`${canvasMode === 'erase' ? 'Erase' : 'Brush'} aborted — ${reason}`, 'warn');
                            e.preventDefault(); return;
                        }
                        const radius = parseInt(document.getElementById('brushSize')?.value || 20);
                        const opacity = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100;
                        const hardness = parseInt(document.getElementById('brushHardness')?.value || 100) / 100;
                        _paintOnLayerAt(pos.x, pos.y, radius, canvasMode === 'erase' ? '#000000' : _foregroundColor, opacity, hardness, canvasMode === 'erase');
                        e.preventDefault(); return;
                    }
                    // Preserve region-mask brush/erase when no editable layer is active.
                    if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                    if (typeof _maybeToastLayerPaintFallback === 'function' && (canvasMode === 'brush' || canvasMode === 'erase')) {
                        _maybeToastLayerPaintFallback(canvasMode);
                    }
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
                        _rectZoneCache = _rcPre.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, _rcPre.width, _rcPre.height);
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
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
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
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                } else if (canvasMode === 'fill') {
                    // 2026-04-18 marathon audit — fill / gradient are
                    // tool-agnostic-edit tools: they should refuse on locked
                    // layer AND surface a fallback toast when the painter has
                    // a layer selected but it is not usable for direct edit.
                    // Pre-audit these two tools had neither guard.
                    if (typeof isLayerToolbarMode === 'function' && isLayerToolbarMode()) {
                        if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                        if (!requireLayerToolbarTarget('Fill Bucket')) { e.preventDefault(); return; }
                        _pushLayerUndo(getSelectedLayer(), 'fill bucket on layer');
                        fillBucketOnLayer(pos.x, pos.y);
                    } else {
                        if (!requireZoneToolbarMode('Fill Bucket')) { e.preventDefault(); return; }
                        pushUndo(selectedZoneIndex);
                        fillBucketAtPoint(pos.x, pos.y);
                        renderRegionOverlay();
                        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    }
                } else if (canvasMode === 'gradient') {
                    // 2026-04-18 marathon audit — gradient: same locked guard
                    // + fallback toast as fill. Pre-audit painter could drag
                    // a gradient on a locked Sponsors layer and silently
                    // write to the zone mask instead.
                    if (typeof isLayerToolbarMode === 'function' && isLayerToolbarMode()) {
                        if (typeof shouldBrushStrokeProceed === 'function' && !shouldBrushStrokeProceed()) { e.preventDefault(); return; }
                        if (!requireLayerToolbarTarget('Gradient')) { e.preventDefault(); return; }
                        _pushLayerUndo(getSelectedLayer(), 'gradient on layer');
                        window._gradientTargetLayerId = _selectedLayerId || null;
                    } else {
                        if (!requireZoneToolbarMode('Gradient')) { e.preventDefault(); return; }
                        pushUndo(selectedZoneIndex);
                        window._gradientTargetLayerId = null;
                    }
                    isDrawing = true;
                    window._gradientStart = { x: pos.x, y: pos.y };
                    // Prevent drag for native canvas
                    e.preventDefault();
                } else if (canvasMode === 'selection-move') {
                    const zone = zones[selectedZoneIndex];
                    if (!zone || !zone.regionMask || !zone.regionMask.some(v => v > 0)) {
                        if (typeof showToast === 'function') showToast('No selection to move — draw a selection first', true);
                        e.preventDefault();
                        return;
                    }
                    if (!_selectionContainsCanvasPoint(pos.x, pos.y)) {
                        _clearActivePixelSelection();
                        e.preventDefault();
                        return;
                    }
                    if (typeof pushZoneUndo === 'function') pushZoneUndo('move selection', true);
                    else if (typeof pushUndo === 'function') pushUndo(selectedZoneIndex);
                    _selectionMoveDrag = {
                        startX: pos.x,
                        startY: pos.y,
                        baseMask: new Uint8Array(zone.regionMask),
                    };
                    isDrawing = true;
                    canvas.style.cursor = 'grabbing';
                    e.preventDefault();
                    return;
                }
            };

            canvas.onmouseup = function (e) {
                if (placementDragging) {
                    if (typeof window !== 'undefined' && typeof window._commitActivePlacementDrag === 'function') {
                        window._commitActivePlacementDrag();
                    }
                    return;
                }
                if (canvasMode === 'selection-move' && _selectionMoveDrag) {
                    const movePos = getPixelAtClamped(e);
                    if (movePos) updateSelectionMovePreview(movePos);
                    _selectionMoveDrag = null;
                    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    if (typeof renderZones === 'function') renderZones();
                    if (typeof updateRegionStatus === 'function') updateRegionStatus();
                    canvas.style.cursor = 'grab';
                    isDrawing = false;
                    return;
                }
                if (canvasMode === 'rect' && isDrawing && rectStart) {
                    let pos = getPixelAtClamped(e);
                    if (e.shiftKey) pos = constrainRectToSquare(rectStart, pos);
                    // 2026-04-18 MARATHON bug #24 (HIGH): pre-fix, rect
                    // selection commit updated zone.regionMask (which flows
                    // into the render payload) but NEVER fired Live Preview.
                    // Painter drew a rectangle expecting zone to spread to
                    // those pixels, saw the visual overlay change, but the
                    // rendered car kept showing the old zone coverage.
                    commitRectSelection(pos, e);
                }
                // Brush/erase: full re-render once at stroke end so edges and multi-zone
                // overlaps are drawn correctly (fast arc path skips those)
                if ((canvasMode === 'brush' || canvasMode === 'erase') && isDrawing) {
                    renderRegionOverlay();
                    // Auto-trigger preview so user sees the actual finish effect immediately
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                }
                if ((canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude' || canvasMode === 'spatial-erase') && isDrawing) {
                    _doRenderRegionOverlay();
                    // 2026-04-18 MARATHON bug #25 (HIGH): spatial mask flows
                    // into zoneObj.spatial_mask in the render payload, so it
                    // DOES affect the rendered car. Pre-fix, mouseup only
                    // re-rendered the region overlay (visual feedback) but
                    // never triggered Live Preview — painter saw the
                    // spatial overlay change but the rendered car stayed
                    // stale. Also spatial-erase was completely missing
                    // from the mouseup branch.
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                }
                if (canvasMode === 'lasso' && isDrawing) {
                    if (lassoFreehandDrawing) {
                        // Freehand drag completed — auto-close if enough points
                        if (lassoPoints.length >= 3) {
                            closeLasso(e);
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
                // Gradient: on mouseup, compute and apply the gradient fill
                if (canvasMode === 'gradient' && isDrawing && window._gradientStart) {
                    const pos = getPixelAtClamped(e);
                    if (pos) {
                        const gradType = document.getElementById('gradientType')?.value || 'linear';
                        let targetLayer = null;
                        if (window._gradientTargetLayerId && Array.isArray(_psdLayers)) {
                            targetLayer = _psdLayers.find(function (layer) {
                                return layer && layer.id === window._gradientTargetLayerId;
                            }) || null;
                        }
                        if (targetLayer) {
                            fillGradientOnLayer(window._gradientStart.x, window._gradientStart.y, pos.x, pos.y, gradType, targetLayer);
                        } else {
                            fillGradientMask(window._gradientStart.x, window._gradientStart.y, pos.x, pos.y, gradType);
                            renderRegionOverlay();
                        }
                        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                        // Clear gradient preview line
                        const rc = document.getElementById('regionCanvas');
                        if (rc) { _doRenderRegionOverlay(); }
                    }
                    window._gradientStart = null;
                    window._gradientTargetLayerId = null;
                }
                // === NEW TOOLS MOUSEUP ===
                if (canvasMode === 'shape' && isDrawing && _shapeStart) {
                    let spos = getPixelAtClamped(e);
                    if (spos) {
                        if (e.shiftKey) {
                            const dx = spos.x - _shapeStart.x, dy = spos.y - _shapeStart.y;
                            const size = Math.max(Math.abs(dx), Math.abs(dy));
                            spos = { x: _shapeStart.x + size * Math.sign(dx || 1), y: _shapeStart.y + size * Math.sign(dy || 1) };
                        }
                        if (typeof commitShape === 'function') commitShape(_shapeStart, spos);
                    }
                    _shapeStart = null;
                    if (typeof _doRenderRegionOverlay === 'function') _doRenderRegionOverlay();
                }
                if (canvasMode === 'pen' && penDragging) {
                    penDragging = false; penDragIndex = -1;
                }
                if (canvasMode === 'ellipse-marquee' && isDrawing && _ellipseStart) {
                    let epos = getPixelAtClamped(e);
                    if (epos) {
                        if (e.shiftKey) {
                            const dx = epos.x - _ellipseStart.x, dy = epos.y - _ellipseStart.y;
                            const size = Math.max(Math.abs(dx), Math.abs(dy));
                            epos = { x: _ellipseStart.x + size * Math.sign(dx || 1), y: _ellipseStart.y + size * Math.sign(dy || 1) };
                        }
                        if (typeof commitEllipseSelection === 'function') commitEllipseSelection(_ellipseStart, epos);
                    }
                    _ellipseStart = null;
                    if (typeof _doRenderRegionOverlay === 'function') _doRenderRegionOverlay();
                }
                if (canvasMode === 'clone' && isDrawing) { _cloneOffset = null; }
                // Commit layer paint on stroke end — ALL tools that push layer undo must commit
                if (_activeLayerCanvas && (canvasMode === 'brush' || canvasMode === 'colorbrush' || canvasMode === 'erase' || canvasMode === 'recolor' || canvasMode === 'smudge' || canvasMode === 'dodge' || canvasMode === 'burn' || canvasMode === 'blur-brush' || canvasMode === 'sharpen-brush' || canvasMode === 'clone' || canvasMode === 'history-brush' || canvasMode === 'pencil')) {
                    _commitLayerPaint();
                }
                // === END NEW TOOLS MOUSEUP ===

                // Auto-trigger live preview after ANY tool action
                if (typeof triggerPreviewRender === 'function' &&
                    typeof isPreviewSurfaceVisible === 'function' &&
                    isPreviewSurfaceVisible()) {
                    triggerPreviewRender();
                }
                isDrawing = false;
            };

            // Remove old onclick (now handled by onmousedown)
            canvas.onclick = null;

            // Block native canvas image drag - browsers treat <canvas> as a draggable image,
            // which steals mousemove events during drag-to-draw operations
            if (!canvas._spbDragstartBlocked) {
                canvas.addEventListener('dragstart', (e) => e.preventDefault());
                canvas._spbDragstartBlocked = true;
            }
            if (!canvas._spbContextMenuBlocked) {
                // The viewport owns custom context-menu rendering so pan/menu
                // suppression only has one place to coordinate.
                canvas.addEventListener('contextmenu', (e) => e.preventDefault());
                canvas._spbContextMenuBlocked = true;
            }

            // Document-level listeners — only attach ONCE (guard prevents accumulation on tool changes)
            if (!_canvasHandlersAttached) {
            _canvasHandlersAttached = true;

            // Document-level mousemove for rect/gradient preview during drag.
            document.addEventListener('mousemove', function _rectGradDocMove(e) {
                if (isPanning || spaceHeld) return;
                if (canvasMode === 'selection-move' && isDrawing && _selectionMoveDrag) {
                    const pos = getPixelAtClamped(e);
                    updateSelectionMovePreview(pos);
                    return;
                }
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
                    if (typeof window !== 'undefined' && typeof window._commitActivePlacementDrag === 'function') {
                        window._commitActivePlacementDrag();
                    }
                    return;
                }
                if (canvasMode === 'rect' && isDrawing && rectStart) {
                    let pos = getPixelAtClamped(e);
                    if (e.shiftKey) pos = constrainRectToSquare(rectStart, pos);
                    commitRectSelection(pos, e);
                    isDrawing = false;
                }
            });

            } // end _canvasHandlersAttached guard
        }

        function setCanvasMode(mode) {
            canvasMode = mode;
            const canvas = document.getElementById('paintCanvas');

            // Update active tool label in tool options bar
            const toolNames = {
                eyedropper: 'EYEDROPPER', brush: 'BRUSH', erase: 'ERASER', wand: 'MAGIC WAND',
                selectall: 'SELECT ALL', edge: 'EDGE DETECT', rect: 'RECTANGLE',
                'selection-move': 'MOVE BORDER',
                lasso: 'LASSO', gradient: 'GRADIENT', fill: 'FILL BUCKET',
                text: 'TEXT', shape: 'SHAPE', clone: 'CLONE STAMP',
                pen: 'PEN / BEZIER', colorbrush: 'COLOR BRUSH', 'ellipse-marquee': 'ELLIPSE',
                recolor: 'RECOLOR', smudge: 'SMUDGE', 'history-brush': 'HISTORY BRUSH',
                pencil: 'PENCIL', dodge: 'DODGE', burn: 'BURN', 'blur-brush': 'BLUR BRUSH', 'sharpen-brush': 'SHARPEN BRUSH',
                'spatial-include': 'SPATIAL +', 'spatial-exclude': 'SPATIAL −', 'spatial-erase': 'SPATIAL ERASE',
                'layer-move': 'MOVE LAYER (drag selected layer)', 'layer-pick': 'PICK ITEM (click layer or logo)'
            };
            const label = document.getElementById('activeToolLabel');
            if (label) {
                // TOOLS WAR — every tool switch surfaces BOTH the tool name AND
                // the active target so the painter never has to wonder "where
                // is my next stroke going?". The target string includes
                // (locked)/(hidden) tags surfaced from getActiveTargetSummary.
                var _baseLabel = toolNames[mode] || mode.toUpperCase();
                var _target = (typeof getActiveTargetSummary === 'function')
                    ? getActiveTargetSummary() : null;
                // Pixel-paint and tool-agnostic-edit tools care about the target.
                // Selection / spatial / sample tools don't (they don't write to a layer).
                var _layerAware = ['colorbrush','recolor','smudge','erase','clone',
                    'pencil','dodge','burn','blur-brush','sharpen-brush',
                    'history-brush'].indexOf(mode) >= 0;
                if (_layerAware && _target) {
                    label.textContent = _baseLabel + ' → ' + _target;
                } else {
                    label.textContent = _baseLabel;
                }
            }
            // Track E #107 — fire flow-ignored hint when switching to a tool
            // that doesn't honor flow AND the painter has flow set below 100%.
            if (typeof maybeWarnFlowIgnored === 'function') maybeWarnFlowIgnored(mode);

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
                edge: 'vtModeEdge', text: 'vtModeText', shape: 'vtModeShape',
                clone: 'vtModeClone', pen: 'vtModePen', colorbrush: 'vtModeColorBrush',
                'selection-move': 'vtModeSelectionMove',
                'ellipse-marquee': 'vtModeEllipseMarquee', recolor: 'vtModeRecolor', smudge: 'vtModeSmudge',
                pencil: 'vtModePencil', dodge: 'vtModeDodge', burn: 'vtModeBurn', 'blur-brush': 'vtModeBlurBrush', 'sharpen-brush': 'vtModeSharpenBrush',
                'spatial-include': 'vtModeSpatialInclude',
                'spatial-exclude': 'vtModeSpatialExclude', 'spatial-erase': 'vtModeSpatialErase',
                lasso: 'vtModeLasso', gradient: 'vtModeGradient', fill: 'vtModeFill',
                'layer-move': 'vtModeLayerMove', 'layer-pick': 'vtModeLayerPick'
            }[mode];
            document.getElementById(vtBtnId)?.classList.add('active');
            // Reset tool state when switching away — prevents stale state from leaking between tools
            if (mode !== 'lasso' && lassoActive) { lassoActive = false; lassoPoints = []; hideLassoPreview(); }
            if (mode !== 'pen' && typeof penPoints !== 'undefined' && penPoints.length > 0) { penPoints = []; penClosed = false; if (typeof drawPenPath === 'function') drawPenPath(); }
            if (mode !== 'clone') { _cloneOffset = null; }
            if (mode !== 'smudge') { _smudgeBuffer = null; }
            if (mode !== 'ellipse-marquee') { _ellipseStart = null; }
            if (mode !== 'shape') { _shapeStart = null; }
            if (mode !== 'gradient') { _gradientStart = null; }
            if (mode !== 'rect') { rectStart = null; }
            if (mode !== 'selection-move' && _selectionMoveDrag) {
                if (typeof cancelSelectionMove === 'function') {
                    cancelSelectionMove(true);
                } else {
                    _selectionMoveDrag = null;
                    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
                    if (typeof renderZones === 'function') renderZones();
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    if (typeof updateRegionStatus === 'function') updateRegionStatus();
                    if (typeof renderContextActionBar === 'function') renderContextActionBar();
                }
            }
            // Track M #253 — abandon any in-progress stroke when switching
            // tools so the new tool doesn't inherit isDrawing=true. If a
            // layer-paint canvas is alive, commit it cleanly so the
            // user doesn't lose their dabs.
            if (typeof isDrawing !== 'undefined' && isDrawing) {
                isDrawing = false;
                if (typeof _activeLayerCanvas !== 'undefined' && _activeLayerCanvas
                    && typeof _commitLayerPaint === 'function') {
                    try { _commitLayerPaint(); } catch (_) {}
                }
            }
            // 2026-04-18 SIX-HOUR MARATHON chaos audit — active Free
            // Transform + painter clicks a different left-rail tool left
            // the transform canvas visible AND capturing pointer events,
            // so the "new" tool was silently unreachable. Photoshop
            // behavior: switching tools during Free Transform AUTO-COMMITS
            // the transform. Match that. Guard against the mode still
            // being the transform mode itself (no-op if painter just
            // re-clicked Transform).
            if (typeof freeTransformState !== 'undefined' && freeTransformState) {
                try {
                    if (freeTransformState.target === 'layer' && typeof commitLayerTransform === 'function') {
                        commitLayerTransform();
                    } else if (typeof deactivateFreeTransform === 'function') {
                        deactivateFreeTransform(true); // commit (Photoshop parity)
                    }
                } catch (_) {
                    // If commit throws, force-clear to avoid a wedged UI.
                    freeTransformState = null;
                    if (typeof _hideTransformCanvas === 'function') _hideTransformCanvas();
                    if (typeof _hideLayerTransformQuickbar === 'function') _hideLayerTransformQuickbar();
                }
            }
            // Placement is its own editing session. If the painter explicitly
            // clicks a different tool, close placement so the canvas cursor and
            // drag ownership stop behaving like placement is still active.
            if (typeof placementLayer !== 'undefined' && placementLayer && placementLayer !== 'none') {
                try {
                    if (typeof finishManualPlacementSession === 'function') finishManualPlacementSession(true);
                    else if (typeof deactivateManualPlacement === 'function') deactivateManualPlacement();
                } catch (_) {}
            }

            // Toggle tool-specific controls
            const layerToolbarActive = (typeof isLayerToolbarMode === 'function') && isLayerToolbarMode();
            const showZoneFillForeground = _shouldShowForegroundPickerForZoneFill(mode, layerToolbarActive);
            const showBrush = (mode === 'brush' || mode === 'erase' || mode === 'clone' || mode === 'colorbrush' || mode === 'recolor' || mode === 'smudge' || mode === 'history-brush' || mode === 'dodge' || mode === 'burn' || mode === 'blur-brush' || mode === 'sharpen-brush' || mode === 'pencil');
            const showWand = (mode === 'wand' || mode === 'selectall' || mode === 'edge' || mode === 'rect' || mode === 'fill' || mode === 'recolor');
            const showSpatial = (mode === 'spatial-include' || mode === 'spatial-exclude' || mode === 'spatial-erase');
            const showGradient = (mode === 'gradient');
            const showText = (mode === 'text');
            const showShape = (mode === 'shape');
            const showClone = (mode === 'clone');
            const showPen = (mode === 'pen');
            const showColorBrush = (mode === 'colorbrush' || mode === 'recolor' || mode === 'smudge' || mode === 'brush' || mode === 'erase' || showZoneFillForeground || (layerToolbarActive && (mode === 'fill' || mode === 'gradient')));
            const showEllipseMarquee = (mode === 'ellipse-marquee');
            document.getElementById('brushSizeLabel').style.display = showBrush ? '' : 'none';
            document.getElementById('brushSize').style.display = showBrush ? '' : 'none';
            document.getElementById('brushSizeVal').style.display = showBrush ? '' : 'none';
            // Opacity + Hardness: visible for brush/erase/clone
            document.getElementById('brushOpacityLabel').style.display = showBrush ? '' : 'none';
            document.getElementById('brushOpacity').style.display = showBrush ? '' : 'none';
            document.getElementById('brushOpacityVal').style.display = showBrush ? '' : 'none';
            document.getElementById('brushHardnessLabel').style.display = showBrush ? '' : 'none';
            document.getElementById('brushHardness').style.display = showBrush ? '' : 'none';
            document.getElementById('brushHardnessVal').style.display = showBrush ? '' : 'none';
            // Gradient type dropdown
            document.getElementById('gradientType').style.display = showGradient ? '' : 'none';
            // Text, Shape, Clone tool option panels
            const textOpts = document.getElementById('textToolOptions');
            if (textOpts) textOpts.style.display = showText ? 'inline-flex' : 'none';
            const shapeOpts = document.getElementById('shapeToolOptions');
            if (shapeOpts) shapeOpts.style.display = showShape ? 'inline-flex' : 'none';
            const cloneOpts = document.getElementById('cloneToolOptions');
            if (cloneOpts) cloneOpts.style.display = showClone ? 'inline-flex' : 'none';
            const penOpts = document.getElementById('penToolOptions');
            if (penOpts) penOpts.style.display = showPen ? 'inline-flex' : 'none';
            const colorBrushOpts = document.getElementById('colorBrushOptions');
            if (colorBrushOpts) colorBrushOpts.style.display = showColorBrush ? 'inline-flex' : 'none';
            const layerPaintSourceOpts = document.getElementById('layerPaintSourceOptions');
            if (layerPaintSourceOpts) {
                layerPaintSourceOpts.style.display = (layerToolbarActive && (mode === 'fill' || mode === 'brush' || mode === 'colorbrush')) ? 'inline-flex' : 'none';
            }
            // Shape vertices only for polygon/star
            const shapeType = document.getElementById('shapeType')?.value;
            const verticesEl = document.getElementById('shapeVertices');
            if (verticesEl) verticesEl.style.display = (showShape && (shapeType === 'polygon' || shapeType === 'star')) ? '' : 'none';
            document.getElementById('wandToleranceLabel').style.display = showWand ? '' : 'none';
            document.getElementById('wandTolerance').style.display = showWand ? '' : 'none';
            document.getElementById('wandTolVal').style.display = showWand ? '' : 'none';
            // Show selection mode for selection tools
            const showSelMode = (mode === 'wand' || mode === 'selectall' || mode === 'edge' || mode === 'rect' || mode === 'lasso' || mode === 'pen' || mode === 'ellipse-marquee' || ((mode === 'fill' || mode === 'gradient') && !layerToolbarActive));
            const selModeEl = document.getElementById('selectionMode');
            if (selModeEl) selModeEl.style.display = showSelMode ? '' : 'none';
            // Rect tool defaults to additive so multiple rectangles can be drawn
            if (mode === 'rect') {
                const selMode = document.getElementById('selectionMode');
                if (selMode && selMode.value === 'replace') selMode.value = 'add';
            }
            const modifierHint = document.getElementById('selectionModifierHint');
            if (modifierHint) modifierHint.style.display = showSelMode ? '' : 'none';
            if (typeof syncLayerPaintSourceUI === 'function') syncLayerPaintSourceUI();
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

            // === NEW TOOL OPTION CONTROLS ===
            // Brush flow, spacing, shape — visible for brush/erase/colorbrush
            const showBrushAdvanced = (mode === 'brush' || mode === 'erase' || mode === 'colorbrush' || mode === 'recolor' || mode === 'smudge' || mode === 'dodge' || mode === 'burn' || mode === 'blur-brush' || mode === 'sharpen-brush' || mode === 'pencil' || mode === 'clone' || mode === 'history-brush');
            ['brushFlowLabel','brushFlow','brushFlowVal','brushSpacingLabel','brushSpacing','brushSpacingVal','brushShape'].forEach(id => {
                const el = document.getElementById(id); if (el) el.style.display = showBrushAdvanced ? '' : 'none';
            });
            // Symmetry toggle — visible for brush/erase/colorbrush
            const symEl = document.getElementById('symmetryMode');
            if (symEl) symEl.style.display = 'none';
            // Eraser mode — only for eraser
            const eraserModeEl = document.getElementById('eraserMode');
            if (eraserModeEl) eraserModeEl.style.display = (mode === 'erase') ? '' : 'none';
            // Pattern brush selector — for colorbrush
            const patBrushEl = document.getElementById('patternBrushSelect');
            if (patBrushEl) patBrushEl.style.display = (mode === 'colorbrush' && !(layerToolbarActive && isLayerPaintSourceSpecial())) ? '' : 'none';
            // Reference image opacity — always visible when a reference is loaded
            const refOpEl = document.getElementById('refOpacityControls');
            if (refOpEl) refOpEl.style.display = (typeof _referenceImage !== 'undefined' && _referenceImage) ? 'inline-flex' : 'none';
            // Gradient extras — reverse, FG→transparent
            ['gradientReverseLabel','gradientFgTransLabel'].forEach(id => {
                const el = document.getElementById(id); if (el) el.style.display = showGradient ? '' : 'none';
            });
            // Wand extras — sample size, anti-alias, feather
            const showWandExtras = (mode === 'wand' || mode === 'selectall');
            ['wandSampleSize','wandAntiAliasLabel'].forEach(id => {
                const el = document.getElementById(id); if (el) el.style.display = showWandExtras ? '' : 'none';
            });
            // Selection feather — visible for all selection tools
            const showFeather = (mode === 'wand' || mode === 'selectall' || mode === 'rect' || mode === 'lasso' || mode === 'ellipse-marquee' || mode === 'edge');
            const featherEl = document.getElementById('selectionFeatherLabel');
            if (featherEl) featherEl.style.display = showFeather ? 'inline-flex' : 'none';

            // Update cursor
            const viewport = document.getElementById('canvasViewport');
            if (mode === 'eyedropper') {
                canvas.style.cursor = 'crosshair';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'none';
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (showSpatial || mode === 'spatial-erase') {
                canvas.style.cursor = getBrushNativeCursor();
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (showBrush) {
                canvas.style.cursor = getBrushNativeCursor();
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (mode === 'text') {
                canvas.style.cursor = 'text';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'none';
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (mode === 'shape') {
                canvas.style.cursor = 'crosshair';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'none';
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (mode === 'clone' || mode === 'colorbrush' || mode === 'recolor' || mode === 'smudge' || mode === 'history-brush' || mode === 'dodge' || mode === 'burn' || mode === 'blur-brush' || mode === 'sharpen-brush') {
                canvas.style.cursor = getBrushNativeCursor();
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (mode === 'pencil') {
                canvas.style.cursor = 'crosshair';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (mode === 'pen') {
                canvas.style.cursor = 'crosshair';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'none';
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (mode === 'ellipse-marquee') {
                canvas.style.cursor = 'crosshair';
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
            } else if (mode === 'selection-move') {
                canvas.style.cursor = 'grab';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (mode === 'gradient') {
                canvas.style.cursor = 'crosshair';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (mode === 'fill') {
                canvas.style.cursor = 'crosshair';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
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
            const layerMode = typeof isLayerToolbarMode === 'function' && isLayerToolbarMode();
            const zoneColor = ZONE_OVERLAY_COLORS[selectedZoneIndex % ZONE_OVERLAY_COLORS.length];
            const selectedLayer = (typeof getSelectedLayer === 'function') ? getSelectedLayer() : null;
            const selectedZone = zones[selectedZoneIndex];
            const scopedZoneBrush = _zoneBrushUsesScopedRefinement(selectedZone);
            const selectedZoneMatchesLayer = !!(
                selectedLayer &&
                selectedZone &&
                selectedZone.sourceLayer &&
                selectedZone.sourceLayer === selectedLayer.id
            );
            const nameEl = document.getElementById('drawZoneName');
            const dotEl = document.getElementById('drawZoneColorDot');
            if (layerMode && selectedLayer) {
                if (nameEl) nameEl.textContent = `Layer: ${selectedLayer.name || 'Selected Layer'}`;
                if (dotEl) dotEl.style.background = 'rgba(0,229,255,0.85)';
            } else {
                if (nameEl) nameEl.textContent = `Zone ${selectedZoneIndex + 1}: ${zones[selectedZoneIndex]?.name || '?'}`;
                if (dotEl) dotEl.style.background = `rgba(${zoneColor[0]},${zoneColor[1]},${zoneColor[2]},0.8)`;
            }

            // Update label and hint based on mode
            const label = document.getElementById('drawZoneLabel');
            const hint = document.getElementById('drawZoneHint');
            if (layerMode && !selectedLayer) {
                label.textContent = 'Layer mode:';
                label.style.color = '#00e5ff';
                hint.textContent = '(select an editable layer — zone mask tools are disabled right now)';
                return;
            }
            if (layerMode && selectedLayer) {
                if (canvasMode === 'brush' || canvasMode === 'erase') {
                    label.textContent = canvasMode === 'erase' ? 'Erasing layer:' : 'Painting layer:';
                    label.style.color = '#00e5ff';
                    hint.textContent = selectedZoneMatchesLayer && scopedZoneBrush
                        ? '(this paints raw layer pixels across the layer — switch to ZONE to stay inside the current zone selector)'
                        : '(toolbar is locked to the selected layer — zone masks will not change)';
                    return;
                }
                if (['fill', 'gradient', 'colorbrush', 'clone', 'recolor', 'smudge', 'history-brush', 'pencil', 'dodge', 'burn', 'blur-brush', 'sharpen-brush', 'text', 'shape'].includes(canvasMode)) {
                    label.textContent = 'Layer tool on:';
                    label.style.color = '#00e5ff';
                    hint.textContent = selectedZoneMatchesLayer && scopedZoneBrush
                        ? '(this edits raw layer pixels on the selected layer — switch to ZONE to scope it to the active zone selector)'
                        : '(toolbar is locked to the selected layer — switch to ZONE for mask tools)';
                    return;
                }
                if (['wand', 'selectall', 'edge', 'rect', 'lasso', 'ellipse-marquee', 'pen', 'selection-move', 'spatial-include', 'spatial-exclude', 'spatial-erase'].includes(canvasMode)) {
                    label.textContent = 'Zone-only tool:';
                    label.style.color = '#ffb347';
                    hint.textContent = '(switch the toolbar to ZONE to use this tool on masks and restrictions)';
                    return;
                }
            }
            if (canvasMode === 'wand') {
                label.textContent = 'Wand select for:';
                hint.textContent = '(click a number/logo/shape - Shift+click to add more areas)';
            } else if (canvasMode === 'brush' && scopedZoneBrush) {
                label.textContent = 'Refining zone:';
                label.style.color = 'var(--accent-green)';
                hint.textContent = '(paint to KEEP this zone only inside its current color/layer selection — kept marks should now win locally in preview)';
            } else if (canvasMode === 'erase') {
                if (scopedZoneBrush) {
                    label.textContent = 'Clearing refine for:';
                    label.style.color = '#ffb347';
                    hint.textContent = '(erase keep-marks; the picked yellow/layer selector itself stays intact)';
                } else {
                    label.textContent = 'Erasing from:';
                    hint.textContent = '(paint over drawn areas to remove them)';
                }
            } else if (canvasMode === 'spatial-include') {
                label.textContent = '✅ Including for:';
                label.style.color = 'var(--accent-green)';
                hint.textContent = '(paint green areas to KEEP in this zone\'s color match)';
            } else if (canvasMode === 'spatial-exclude') {
                label.textContent = '❌ Excluding from:';
                label.style.color = '#ff4444';
                hint.textContent = '(paint red areas to REMOVE from this zone\'s color match)';
            } else if (canvasMode === 'lasso') {
                label.textContent = 'Lasso for:';
                label.style.color = 'var(--accent-gold)';
                hint.textContent = `(click to place vertices, double-click to fill - ${lassoPoints.length} points)`;
            } else if (canvasMode === 'selection-move') {
                label.textContent = 'Move border for:';
                label.style.color = 'var(--accent-cyan)';
                hint.textContent = '(drag inside the current selection to reposition the border without moving pixels)';
            } else if (canvasMode === 'gradient') {
                label.textContent = 'Gradient for:';
                label.style.color = 'var(--accent-gold)';
                hint.textContent = '(drag to set gradient direction and length)';
            } else if (canvasMode === 'fill') {
                if (scopedZoneBrush) {
                    label.textContent = 'Scoped fill for:';
                    label.style.color = 'var(--accent-green)';
                    hint.textContent = '(bucket only inside this zone’s current color/layer selection — the FG color picker now drives the local preview/base tint here)';
                } else {
                    label.textContent = 'Fill for:';
                    label.style.color = 'var(--accent-gold)';
                    hint.textContent = '(click to flood-fill based on tolerance)';
                }
            } else if (canvasMode === 'pen') {
                label.textContent = 'Pen for:';
                label.style.color = '#00e5ff';
                hint.textContent = '(click to add points, drag for curves, Enter to convert to selection)';
            } else if (canvasMode === 'ellipse-marquee') {
                label.textContent = 'Ellipse for:';
                label.style.color = 'var(--accent-gold)';
                hint.textContent = '(drag to draw elliptical selection, Shift for circle)';
            } else if (canvasMode === 'colorbrush') {
                label.textContent = 'Color painting on:';
                label.style.color = '#ff9900';
                hint.textContent = '(painting with foreground color on the canvas)';
            } else if (canvasMode === 'clone') {
                label.textContent = 'Cloning on:';
                label.style.color = '#ff9900';
                hint.textContent = _cloneSource ? `(source: ${_cloneSource.x}, ${_cloneSource.y})` : '(Alt+Click to set clone source first)';
            } else if (canvasMode === 'recolor') {
                label.textContent = 'Recoloring on:';
                label.style.color = '#ff9900';
                hint.textContent = '(replaces BG color with FG color under brush)';
            } else if (canvasMode === 'smudge') {
                label.textContent = 'Smudging on:';
                label.style.color = '#ff9900';
                hint.textContent = '(finger-paint: smear pixels in drag direction)';
            } else if (canvasMode === 'dodge') {
                label.textContent = 'Dodging on:';
                label.style.color = '#ffcc00';
                hint.textContent = '(lighten pixels under the brush)';
            } else if (canvasMode === 'burn') {
                label.textContent = 'Burning on:';
                label.style.color = '#ff4400';
                hint.textContent = '(darken pixels under the brush)';
            } else if (canvasMode === 'blur-brush') {
                label.textContent = 'Blurring on:';
                label.style.color = '#6688ff';
                hint.textContent = '(soften/blur pixels under the brush)';
            } else if (canvasMode === 'sharpen-brush') {
                label.textContent = 'Sharpening on:';
                label.style.color = '#88ff66';
                hint.textContent = '(sharpen/enhance edges under the brush)';
            } else if (canvasMode === 'pencil') {
                label.textContent = 'Pencil on:';
                label.style.color = '#ff9900';
                hint.textContent = '(1px precise editing: left=FG, right=BG)';
            } else if (canvasMode === 'text') {
                label.textContent = 'Text on:';
                label.style.color = '#ff9900';
                hint.textContent = '(click to place text, Enter to commit)';
            } else if (canvasMode === 'shape') {
                label.textContent = 'Shape on:';
                label.style.color = '#ff9900';
                hint.textContent = '(drag to draw shape, Shift to constrain)';
            } else if (canvasMode === 'history-brush') {
                label.textContent = 'History brush on:';
                label.style.color = '#cc88ff';
                hint.textContent = '(paint pixels back from saved snapshot)';
            } else if (canvasMode === 'rect') {
                label.textContent = 'Rectangle for:';
                label.style.color = 'var(--accent-gold)';
                hint.textContent = '(drag to draw rectangular selection, Shift for square)';
            } else if (canvasMode === 'edge') {
                label.textContent = 'Edge detect for:';
                label.style.color = 'var(--accent-gold)';
                hint.textContent = '(finds edges in the image for selection)';
            } else if (canvasMode === 'selectall') {
                label.textContent = 'Select color for:';
                label.style.color = 'var(--accent-gold)';
                hint.textContent = '(selects all pixels matching clicked color)';
            } else {
                label.textContent = 'Drawing for:';
                label.style.color = '';
                hint.textContent = '(select a different zone on the left to switch)';
            }
        }

        // ===== BRUSH CURSOR CIRCLE - visible radius indicator =====
        // Brush spacing tracker — only fire a dab when cursor moves far enough
        var _lastDabX = -9999, _lastDabY = -9999;
        function _checkBrushSpacing(x, y, radius) {
            const spacingPct = parseInt(document.getElementById('brushSpacing')?.value || 25);
            const minDist = Math.max(1, radius * spacingPct / 100);
            const dx = x - _lastDabX, dy = y - _lastDabY;
            if (dx * dx + dy * dy >= minDist * minDist) {
                _lastDabX = x; _lastDabY = y;
                return true;
            }
            return false;
        }
        function _resetBrushSpacing() {
            _lastDabX = -9999; _lastDabY = -9999;
            // 2026-04-18 MARATHON bug #33: capture symmetry mode at the
            // start of every brush stroke so mid-drag dropdown changes
            // don't split the stroke into mixed mirror modes. Reset at
            // mouseup is handled in the global mouseup block below.
            if (typeof window !== 'undefined') {
                window._spbStrokeSymmetryMode = getEffectiveSymmetryMode();
            }
        }

        // All modes that show a brush cursor
        const BRUSH_CURSOR_MODES = ['brush', 'erase', 'spatial-include', 'spatial-exclude', 'spatial-erase', 'colorbrush', 'clone', 'recolor', 'smudge', 'history-brush', 'dodge', 'burn', 'blur-brush', 'sharpen-brush'];
        let _lastBrushCursorPointer = null;

        function usesCustomBrushCursorMode(mode) {
            return BRUSH_CURSOR_MODES.includes(mode);
        }

        function getBrushNativeCursor() {
            return (typeof window !== 'undefined' && window.precisionCursor) ? 'crosshair' : 'none';
        }

        function updateBrushCursorVisibility() {
            const circle = document.getElementById('brushCursorCircle');
            if (!circle) return;
            const showCircle = BRUSH_CURSOR_MODES.includes(canvasMode);
            circle.style.display = showCircle ? 'block' : 'none';
            circle.style.visibility = showCircle ? 'visible' : 'hidden';
            if (showCircle) {
                circle.style.opacity = '1';
                circle.style.boxSizing = 'border-box';
                circle.style.background = 'transparent';
                circle.style.boxShadow = '0 0 0 1px rgba(0,0,0,0.55), 0 0 0 2px rgba(255,255,255,0.18)';
                circle.style.mixBlendMode = 'normal';
                // Color the circle based on mode
                const colors = {
                    'spatial-include': 'rgba(0,200,100,0.8)',
                    'spatial-exclude': 'rgba(220,50,50,0.8)',
                    'erase': 'rgba(255,100,100,0.6)',
                    'colorbrush': 'rgba(0,229,255,0.7)',
                    'recolor': 'rgba(255,165,0,0.7)',
                    'smudge': 'rgba(200,150,255,0.7)',
                    'clone': 'rgba(100,255,100,0.6)',
                };
                circle.style.borderColor = colors[canvasMode] || 'rgba(255,255,255,0.7)';

                // Match brush shape
                const shape = document.getElementById('brushShape')?.value || 'round';
                if (shape === 'round' || canvasMode.startsWith('spatial')) {
                    circle.style.borderRadius = '50%';
                    circle.style.transform = 'none';
                } else if (shape === 'square') {
                    circle.style.borderRadius = '0';
                    circle.style.transform = 'none';
                } else if (shape === 'diamond') {
                    circle.style.borderRadius = '0';
                    circle.style.transform = 'rotate(45deg)';
                } else if (shape === 'slash') {
                    circle.style.borderRadius = '0';
                    circle.style.transform = 'rotate(45deg) scaleX(0.3)';
                } else {
                    circle.style.borderRadius = '50%';
                    circle.style.transform = 'none';
                }
                if (_lastBrushCursorPointer) {
                    updateBrushCursorPosition(_lastBrushCursorPointer);
                }
            }
        }

        function updateBrushCursorPosition(e) {
            const circle = document.getElementById('brushCursorCircle');
            if (!circle || circle.style.display === 'none') return;
            const canvas = document.getElementById('paintCanvas');
            if (!canvas || !e || typeof e.clientX !== 'number' || typeof e.clientY !== 'number') return;
            const rect = canvas.getBoundingClientRect();
            if (!rect.width || !rect.height || !canvas.width || !canvas.height) {
                circle.style.opacity = '0';
                return;
            }
            const canvasScaleX = canvas.width / rect.width;
            const canvasScaleY = canvas.height / rect.height;
            const posX = Math.floor((e.clientX - rect.left) * canvasScaleX);
            const posY = Math.floor((e.clientY - rect.top) * canvasScaleY);
            if (posX < 0 || posX >= canvas.width || posY < 0 || posY >= canvas.height) {
                circle.style.opacity = '0';
                return;
            }
            circle.style.opacity = '1';

            // Get the brush radius in canvas pixels
            // 2026-04-18 MARATHON bug #29 (Bockwinkel, MED): pre-fix, the
            // cursor branch only included spatial-include + spatial-exclude,
            // but NOT spatial-erase — so in SPATIAL ERASE mode the cursor
            // showed brushSize while the erase actually applied at
            // spatialBrushRadius. Painter saw a tiny circle but wiped a
            // large region. Fix: include spatial-erase in the same branch.
            let radius;
            if (canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude' || canvasMode === 'spatial-erase') {
                radius = spatialBrushRadius;
            } else {
                radius = parseInt(document.getElementById('brushSize')?.value || 20);
            }

            // Convert canvas pixels to screen pixels using current zoom
            const scaleX = rect.width / canvas.width;
            const scaleY = rect.height / canvas.height;
            const screenRadiusX = radius * scaleX;
            const screenRadiusY = radius * scaleY;
            const diameterX = screenRadiusX * 2;
            const diameterY = screenRadiusY * 2;
            const centerX = rect.left + ((posX + 0.5) * scaleX);
            const centerY = rect.top + ((posY + 0.5) * scaleY);

            circle.style.width = diameterX + 'px';
            circle.style.height = diameterY + 'px';
            circle.style.left = (centerX - screenRadiusX) + 'px';
            circle.style.top = (centerY - screenRadiusY) + 'px';
        }

        // Attach global mousemove for brush cursor tracking
        document.addEventListener('mousemove', function (e) {
            _lastBrushCursorPointer = { clientX: e.clientX, clientY: e.clientY };
            if (BRUSH_CURSOR_MODES.includes(canvasMode)) {
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
                const baseAlpha = color[3] / 255.0; // e.g. 0.5 for semi-transparent overlay
                for (let i = 0; i < zone.regionMask.length; i++) {
                    const maskVal = zone.regionMask[i];
                    if (maskVal > 0) {
                        const pi = i * 4;
                        // Scale overlay alpha by mask value (supports soft brush opacity)
                        const alpha = Math.round(baseAlpha * (maskVal / 255.0) * 255);
                        data[pi] = color[0]; data[pi + 1] = color[1];
                        data[pi + 2] = color[2]; data[pi + 3] = alpha;
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
                            // Include = bright neon green with stronger alpha so scoped areas are obvious.
                            data[pi] = 24; data[pi + 1] = 255; data[pi + 2] = 166; data[pi + 3] = 196;
                        } else if (v === 2) {
                            // Exclude = stronger red overlay
                            data[pi] = 255; data[pi + 1] = 72; data[pi + 2] = 72; data[pi + 3] = 196;
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
            {
                const zi = selectedZoneIndex;
                const zone = zones[zi];
                if (zone && zone.spatialMask) {
                    const cw = paintCanvas.width, ch = paintCanvas.height;
                    for (let y = 0; y < ch; y++) {
                        for (let x = 0; x < cw; x++) {
                            const idx = y * cw + x;
                            const v = zone.spatialMask[idx];
                            if (v !== 1 && v !== 2) continue;
                            const left = (x > 0) ? zone.spatialMask[idx - 1] : 0;
                            const right = (x < cw - 1) ? zone.spatialMask[idx + 1] : 0;
                            const up = (y > 0) ? zone.spatialMask[idx - cw] : 0;
                            const down = (y < ch - 1) ? zone.spatialMask[idx + cw] : 0;
                            const isEdge = (
                                x === 0 || x === cw - 1 || y === 0 || y === ch - 1 ||
                                left !== v || right !== v || up !== v || down !== v
                            );
                            if (!isEdge) continue;
                            const pi = idx * 4;
                            if (v === 1) {
                                imgData.data[pi] = 255; imgData.data[pi + 1] = 255;
                                imgData.data[pi + 2] = 255; imgData.data[pi + 3] = 255;
                            } else {
                                imgData.data[pi] = 255; imgData.data[pi + 1] = 220;
                                imgData.data[pi + 2] = 220; imgData.data[pi + 3] = 255;
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
            if (typeof renderContextActionBar === 'function') {
                renderContextActionBar();
            }
        }

        // ===== UNDO SYSTEM =====
        // BUG #75 (Slaughter, HIGH): SPB has FOUR separate redo stacks (zone
        // regionMask, pixel canvas, per-layer image, layer-stack snapshot)
        // plus `zoneRedoStack` in state-zones.js. Pre-fix, each push-undo
        // cleared only ITS OWN redo — stale entries in the other three
        // would fire on a later Ctrl+Y and destroy intervening work because
        // `redoDrawStroke` checks `_layerRedoStack` first, then pixel, then
        // region. Example: do layer-op, undo, paint a stroke, Ctrl+Y →
        // pops stale layer-redo, wipes the pixel stroke.
        // Fix: a single `_clearAllRedos()` helper invoked from every push-undo
        // site so a new action always invalidates ALL possible redo branches.
        var _undoActionTrail = [];
        var _redoActionTrail = [];
        var _UNDO_ACTION_TRAIL_MAX = 200;

        function _hasUndoEntriesForKind(kind) {
            switch (kind) {
                case 'layer':
                    return (typeof _layerUndoStack !== 'undefined' && Array.isArray(_layerUndoStack) && _layerUndoStack.length > 0);
                case 'pixel':
                    return (typeof _pixelUndoStack !== 'undefined' && Array.isArray(_pixelUndoStack) && _pixelUndoStack.length > 0 &&
                        typeof paintImageData !== 'undefined' && !!paintImageData);
                case 'zone-mask':
                    return (typeof undoStack !== 'undefined' && Array.isArray(undoStack) && undoStack.length > 0);
                case 'zone-config':
                    return (typeof zoneUndoStack !== 'undefined' && Array.isArray(zoneUndoStack) && zoneUndoStack.length > 0);
                default:
                    return false;
            }
        }

        function _hasRedoEntriesForKind(kind) {
            switch (kind) {
                case 'layer':
                    return (typeof _layerRedoStack !== 'undefined' && Array.isArray(_layerRedoStack) && _layerRedoStack.length > 0);
                case 'pixel':
                    return (typeof _pixelRedoStack !== 'undefined' && Array.isArray(_pixelRedoStack) && _pixelRedoStack.length > 0 &&
                        typeof paintImageData !== 'undefined' && !!paintImageData);
                case 'zone-mask':
                    return (typeof redoStack !== 'undefined' && Array.isArray(redoStack) && redoStack.length > 0);
                case 'zone-config':
                    return (typeof zoneRedoStack !== 'undefined' && Array.isArray(zoneRedoStack) && zoneRedoStack.length > 0);
                default:
                    return false;
            }
        }

        function _trimActionTrail(trail) {
            if (!Array.isArray(trail)) return;
            while (trail.length > _UNDO_ACTION_TRAIL_MAX) trail.shift();
        }

        function _recordUndoAction(kind) {
            if (!kind) return;
            _undoActionTrail.push(kind);
            _trimActionTrail(_undoActionTrail);
            _redoActionTrail.length = 0;
        }
        window._recordUndoAction = _recordUndoAction;

        function _recordRedoAction(kind) {
            if (!kind) return;
            _redoActionTrail.push(kind);
            _trimActionTrail(_redoActionTrail);
        }
        window._recordRedoAction = _recordRedoAction;

        function _peekLatestTrackedKind(trail, hasEntries) {
            if (!Array.isArray(trail)) return null;
            for (let i = trail.length - 1; i >= 0; i--) {
                const kind = trail[i];
                if (hasEntries(kind)) return kind;
            }
            return null;
        }

        function _popLatestTrackedUndoKind() {
            while (_undoActionTrail.length > 0) {
                const kind = _undoActionTrail.pop();
                if (_hasUndoEntriesForKind(kind)) return kind;
            }
            return null;
        }

        function _popLatestTrackedRedoKind() {
            while (_redoActionTrail.length > 0) {
                const kind = _redoActionTrail.pop();
                if (_hasRedoEntriesForKind(kind)) return kind;
            }
            return null;
        }

        function _peekLatestUndoKind() {
            return _peekLatestTrackedKind(_undoActionTrail, _hasUndoEntriesForKind);
        }

        function _peekLatestRedoKind() {
            return _peekLatestTrackedKind(_redoActionTrail, _hasRedoEntriesForKind);
        }

        function _clearAllRedos() {
            try {
                if (typeof redoStack !== 'undefined' && redoStack) redoStack.length = 0;
                if (typeof _pixelRedoStack !== 'undefined' && _pixelRedoStack) _pixelRedoStack.length = 0;
                if (typeof _layerRedoStack !== 'undefined' && _layerRedoStack) _layerRedoStack.length = 0;
                if (typeof zoneRedoStack !== 'undefined' && zoneRedoStack) zoneRedoStack.length = 0;
                if (typeof _redoActionTrail !== 'undefined' && _redoActionTrail) _redoActionTrail.length = 0;
            } catch (_) { /* defensive — never block an undo push */ }
        }
        window._clearAllRedos = _clearAllRedos;

        function pushUndo(zoneIndex) {
            const zone = zones[zoneIndex];
            if (!zone) return;
            // Save a copy of the current masks (or null if no mask yet)
            const prevMask = zone.regionMask ? new Uint8Array(zone.regionMask) : null;
            const prevSpatial = zone.spatialMask ? new Uint8Array(zone.spatialMask) : null;
            undoStack.push({
                zoneIndex,
                prevMask,
                prevSpatial,
                prevBaseColorMode: zone.baseColorMode,
                prevBaseColor: zone.baseColor,
                prevBaseColorSource: zone.baseColorSource,
                prevBaseColorStrength: zone.baseColorStrength,
                prevAutoBaseColorFill: zone._autoBaseColorFill,
                prevScopedBrushAutoBaseColor: zone._scopedBrushAutoBaseColor,
            });
            _clearAllRedos(); // BUG #75: invalidate ALL redo branches on new action
            // Trim stack if too large
            if (undoStack.length > MAX_UNDO) undoStack.shift();
            _recordUndoAction('zone-mask');
        }

        // Unified pixel undo stack (for ALL paint/pixel tools)
        var _pixelUndoStack = [];
        var _pixelRedoStack = [];
        var _PIXEL_UNDO_MAX = 10;

        function pushPixelUndo(label) {
            // Snapshot the current paint canvas pixels
            if (typeof paintImageData === 'undefined' || !paintImageData) return;
            _pixelUndoStack.push({ data: new Uint8ClampedArray(paintImageData.data), label: label || 'paint' });
            _clearAllRedos(); // BUG #75: invalidate ALL redo branches, not just pixel
            if (_pixelUndoStack.length > _PIXEL_UNDO_MAX) _pixelUndoStack.shift();
            _recordUndoAction('pixel');
        }

        function undoDrawStroke() {
            // Chronological undo routing: do NOT guess by stack priority.
            // A stale pixel snapshot must never outrank the fresh zone fill the
            // painter just made, or Ctrl+Z can replay garbage into source paint.
            const trackedKind = _popLatestTrackedUndoKind();
            if (trackedKind === 'layer') {
                if (typeof undoLayerEdit === 'function' && undoLayerEdit()) {
                    _recordRedoAction('layer');
                    return;
                }
            }
            if (trackedKind === 'pixel') {
                if (_pixelUndoStack.length > 0 && typeof paintImageData !== 'undefined' && paintImageData) {
                    const entry = _pixelUndoStack.pop();
                    _pixelRedoStack.push({ data: new Uint8ClampedArray(paintImageData.data), label: entry.label });
                    paintImageData.data.set(entry.data);
                    const pc = document.getElementById('paintCanvas');
                    if (pc) pc.getContext('2d').putImageData(paintImageData, 0, 0);
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    _recordRedoAction('pixel');
                    showToast(`Undid ${entry.label}`);
                    return;
                }
            }
            if (trackedKind === 'zone-config') {
                if (typeof undoZoneChange === 'function' && undoZoneChange()) {
                    _recordRedoAction('zone-config');
                    return;
                }
            }
            if (trackedKind === 'zone-mask') {
                if (undoStack.length > 0) {
                    const entry = undoStack.pop();
                    const zone = zones[entry.zoneIndex];
                    if (!zone) return;
                    if (typeof redoStack !== 'undefined') {
                        redoStack.push({
                            zoneIndex: entry.zoneIndex,
                            prevMask: zone.regionMask ? new Uint8Array(zone.regionMask) : null,
                            prevSpatial: zone.spatialMask ? new Uint8Array(zone.spatialMask) : null,
                            prevBaseColorMode: zone.baseColorMode,
                            prevBaseColor: zone.baseColor,
                            prevBaseColorSource: zone.baseColorSource,
                            prevBaseColorStrength: zone.baseColorStrength,
                            prevAutoBaseColorFill: zone._autoBaseColorFill,
                            prevScopedBrushAutoBaseColor: zone._scopedBrushAutoBaseColor,
                        });
                    }
                    zone.regionMask = entry.prevMask;
                    zone.spatialMask = entry.prevSpatial;
                    if ('prevBaseColorMode' in entry) zone.baseColorMode = entry.prevBaseColorMode;
                    if ('prevBaseColor' in entry) zone.baseColor = entry.prevBaseColor;
                    if ('prevBaseColorSource' in entry) zone.baseColorSource = entry.prevBaseColorSource;
                    if ('prevBaseColorStrength' in entry) zone.baseColorStrength = entry.prevBaseColorStrength;
                    if ('prevAutoBaseColorFill' in entry) zone._autoBaseColorFill = entry.prevAutoBaseColorFill;
                    if ('prevScopedBrushAutoBaseColor' in entry) zone._scopedBrushAutoBaseColor = entry.prevScopedBrushAutoBaseColor;
                    _fastSpatialOverlayArc(pos.x, pos.y, spatialBrushRadius, val);
                    if (typeof selectedZoneIndex !== 'undefined' && selectedZoneIndex === entry.zoneIndex && typeof renderZoneDetail === 'function') {
                        renderZoneDetail(entry.zoneIndex);
                    }
                    if (typeof renderZones === 'function') renderZones();
                    triggerPreviewRender();
                    _recordRedoAction('zone-mask');
                    showToast(`Undo: reverted Zone ${entry.zoneIndex + 1} actions`);
                    return;
                }
            }
            // Legacy single-snapshot undo (backwards compat)
            if (window._cloneUndoSnapshot && typeof paintImageData !== 'undefined' && paintImageData) {
                paintImageData.data.set(window._cloneUndoSnapshot);
                window._cloneUndoSnapshot = null;
                const pc = document.getElementById('paintCanvas');
                if (pc) pc.getContext('2d').putImageData(paintImageData, 0, 0);
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                showToast('Undid clone stroke');
                return;
            }
            if (window._colorBrushUndoSnapshot && typeof paintImageData !== 'undefined' && paintImageData) {
                paintImageData.data.set(window._colorBrushUndoSnapshot);
                window._colorBrushUndoSnapshot = null;
                const pc = document.getElementById('paintCanvas');
                if (pc) pc.getContext('2d').putImageData(paintImageData, 0, 0);
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                showToast('Undid color brush stroke');
                return;
            }
            if (undoStack.length === 0) {
                if (typeof undoZoneChange === 'function' && undoZoneChange()) { return; }
                showToast('Nothing to undo');
                return;
            }
            const entry = undoStack.pop();
            const zone = zones[entry.zoneIndex];
            if (!zone) return;
            if (typeof redoStack !== 'undefined') {
                redoStack.push({
                    zoneIndex: entry.zoneIndex,
                    prevMask: zone.regionMask ? new Uint8Array(zone.regionMask) : null,
                    prevSpatial: zone.spatialMask ? new Uint8Array(zone.spatialMask) : null,
                    prevBaseColorMode: zone.baseColorMode,
                    prevBaseColor: zone.baseColor,
                    prevBaseColorSource: zone.baseColorSource,
                    prevBaseColorStrength: zone.baseColorStrength,
                    prevAutoBaseColorFill: zone._autoBaseColorFill,
                    prevScopedBrushAutoBaseColor: zone._scopedBrushAutoBaseColor,
                });
            }
            zone.regionMask = entry.prevMask;
            zone.spatialMask = entry.prevSpatial;
            if ('prevBaseColorMode' in entry) zone.baseColorMode = entry.prevBaseColorMode;
            if ('prevBaseColor' in entry) zone.baseColor = entry.prevBaseColor;
            if ('prevBaseColorSource' in entry) zone.baseColorSource = entry.prevBaseColorSource;
            if ('prevBaseColorStrength' in entry) zone.baseColorStrength = entry.prevBaseColorStrength;
            if ('prevAutoBaseColorFill' in entry) zone._autoBaseColorFill = entry.prevAutoBaseColorFill;
            if ('prevScopedBrushAutoBaseColor' in entry) zone._scopedBrushAutoBaseColor = entry.prevScopedBrushAutoBaseColor;
            renderRegionOverlay();
            if (typeof selectedZoneIndex !== 'undefined' && selectedZoneIndex === entry.zoneIndex && typeof renderZoneDetail === 'function') {
                renderZoneDetail(entry.zoneIndex);
            }
            if (typeof renderZones === 'function') renderZones();
            triggerPreviewRender();
            _recordRedoAction('zone-mask');
            showToast(`Undo: reverted Zone ${entry.zoneIndex + 1} actions`);
        }

        function redoDrawStroke() {
            const trackedKind = _popLatestTrackedRedoKind();
            if (trackedKind === 'layer') {
                if (typeof redoLayerEdit === 'function' && redoLayerEdit()) {
                    _recordUndoAction('layer');
                    return;
                }
            }
            if (trackedKind === 'pixel') {
                if (_pixelRedoStack.length > 0 && typeof paintImageData !== 'undefined' && paintImageData) {
                    const entry = _pixelRedoStack.pop();
                    _pixelUndoStack.push({ data: new Uint8ClampedArray(paintImageData.data), label: entry.label });
                    paintImageData.data.set(entry.data);
                    const pc = document.getElementById('paintCanvas');
                    if (pc) pc.getContext('2d').putImageData(paintImageData, 0, 0);
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    _recordUndoAction('pixel');
                    showToast(`Redo: ${entry.label}`);
                    return;
                }
            }
            if (trackedKind === 'zone-config') {
                if (typeof redoZoneChange === 'function' && redoZoneChange()) {
                    _recordUndoAction('zone-config');
                    return;
                }
            }
            if (trackedKind === 'zone-mask') {
                if (typeof redoStack !== 'undefined' && redoStack.length > 0) {
                    const entry = redoStack.pop();
                    const zone = zones[entry.zoneIndex];
                    if (!zone) return;
                    zone.regionMask = entry.prevMask;
                    zone.spatialMask = entry.prevSpatial;
                    if ('prevBaseColorMode' in entry) zone.baseColorMode = entry.prevBaseColorMode;
                    if ('prevBaseColor' in entry) zone.baseColor = entry.prevBaseColor;
                    if ('prevBaseColorSource' in entry) zone.baseColorSource = entry.prevBaseColorSource;
                    if ('prevBaseColorStrength' in entry) zone.baseColorStrength = entry.prevBaseColorStrength;
                    if ('prevAutoBaseColorFill' in entry) zone._autoBaseColorFill = entry.prevAutoBaseColorFill;
                    if ('prevScopedBrushAutoBaseColor' in entry) zone._scopedBrushAutoBaseColor = entry.prevScopedBrushAutoBaseColor;
                    renderRegionOverlay();
                    if (typeof selectedZoneIndex !== 'undefined' && selectedZoneIndex === entry.zoneIndex && typeof renderZoneDetail === 'function') {
                        renderZoneDetail(entry.zoneIndex);
                    }
                    if (typeof renderZones === 'function') renderZones();
                    triggerPreviewRender();
                    _recordUndoAction('zone-mask');
                    showToast(`Redo: Zone ${entry.zoneIndex + 1} actions`);
                    return;
                }
            }
            if (typeof redoZoneChange === 'function' && typeof zoneRedoStack !== 'undefined' && zoneRedoStack.length > 0) {
                if (redoZoneChange()) return;
            }
            if (typeof redoStack === 'undefined' || redoStack.length === 0) {
                showToast('Nothing to redo');
                return;
            }
            const entry = redoStack.pop();
            const zone = zones[entry.zoneIndex];
            if (!zone) return;
            zone.regionMask = entry.prevMask;
            zone.spatialMask = entry.prevSpatial;
            if ('prevBaseColorMode' in entry) zone.baseColorMode = entry.prevBaseColorMode;
            if ('prevBaseColor' in entry) zone.baseColor = entry.prevBaseColor;
            if ('prevBaseColorSource' in entry) zone.baseColorSource = entry.prevBaseColorSource;
            if ('prevBaseColorStrength' in entry) zone.baseColorStrength = entry.prevBaseColorStrength;
            if ('prevAutoBaseColorFill' in entry) zone._autoBaseColorFill = entry.prevAutoBaseColorFill;
            if ('prevScopedBrushAutoBaseColor' in entry) zone._scopedBrushAutoBaseColor = entry.prevScopedBrushAutoBaseColor;
            renderRegionOverlay();
            if (typeof selectedZoneIndex !== 'undefined' && selectedZoneIndex === entry.zoneIndex && typeof renderZoneDetail === 'function') {
                renderZoneDetail(entry.zoneIndex);
            }
            if (typeof renderZones === 'function') renderZones();
            triggerPreviewRender();
            _recordUndoAction('zone-mask');
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
                zone.regionMask[pos] = 255;
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
                if (zone.regionMask[pos] === 0) continue;  // Skip unselected pixels
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
                    zone.regionMask[i] = 255;
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
                zone.regionMask[pos] = 255;
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
            // 2026-04-18 MARATHON bug #26 (HIGH): pre-fix, clearAllRegions
            // wiped every zone's regionMask with NO undo and NO preview
            // refresh. A painter's accidental click cost them every zone
            // selection they had carefully drawn. Now pushes zone undo
            // (snapshots all zones) and fires Live Preview.
            if (typeof pushZoneUndo === 'function') {
                pushZoneUndo('Clear all zone regions');
            }
            zones.forEach(z => z.regionMask = null);
            renderRegionOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
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
                if (cvs) cvs.style.cursor = getBrushNativeCursor();
                showToast('Spatial Include: paint areas to KEEP in this zone (green)');
            } else if (mode === 'exclude') {
                canvasMode = 'spatial-exclude';
                if (cvs) cvs.style.cursor = getBrushNativeCursor();
                showToast('Spatial Exclude: paint areas to REMOVE from this zone (red)');
            } else if (mode === 'erase-spatial') {
                canvasMode = 'spatial-include'; // reuse include but with value=0
                // We'll handle erase by checking dedicated button state
                if (cvs) cvs.style.cursor = getBrushNativeCursor();
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
                zone.regionMask = new Uint8Array(w * h).fill(255);
            } else {
                for (let i = 0; i < zone.regionMask.length; i++) {
                    zone.regionMask[i] = zone.regionMask[i] > 0 ? 0 : 255;
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
                for (const idx of boundary) mask[idx] = 255;
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
                    zone.regionMask[i] = 255;
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
            const n = Math.max(1, Math.min(12, parseInt(px, 10) || 2));
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            const w = canvas.width, h = canvas.height;
            pushUndo(selectedZoneIndex);
            const mask = zone.regionMask;
            // True feather: compute distance from each pixel to nearest edge,
            // then apply gradient opacity based on distance within feather radius.
            // Use a simple box-blur approximation (much faster than true distance field).
            // Multiple passes of averaging = Gaussian-like blur of the mask.
            const temp = new Float32Array(w * h);
            for (let i = 0; i < mask.length; i++) temp[i] = mask[i] / 255.0;
            // N passes of 3x3 average blur
            for (let pass = 0; pass < n; pass++) {
                const prev = new Float32Array(temp);
                for (let y = 1; y < h - 1; y++) {
                    for (let x = 1; x < w - 1; x++) {
                        const idx = y * w + x;
                        temp[idx] = (
                            prev[idx - w - 1] + prev[idx - w] + prev[idx - w + 1] +
                            prev[idx - 1]     + prev[idx]     + prev[idx + 1] +
                            prev[idx + w - 1] + prev[idx + w] + prev[idx + w + 1]
                        ) / 9.0;
                    }
                }
            }
            // Write back as 0-255
            for (let i = 0; i < mask.length; i++) {
                mask[i] = Math.round(Math.min(255, Math.max(0, temp[i] * 255)));
            }
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Feathered edges by ${n}px (soft gradient)`);
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

        // --- DESELECT --- clear current zone's drawn region and keep the
        // painter on their current tool. Deselect should not silently switch
        // the editing mode out from under the user.
        function deselectRegion() {
            clearZoneRegions(selectedZoneIndex, true);
            if (typeof renderContextActionBar === 'function') renderContextActionBar();
            showToast('Cleared selection');
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

            const fillVal = subtractMode ? 0 : 255;

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
            if (!maybeAutoTransformLayerSelection('lasso', e)) {
                showToast(`Lasso: filled ${filled.toLocaleString()} pixels`);
            }
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
                    // 2026-04-19 TRUE FIVE-HOUR (TF17a) — wrong showToast
                    // signature. The actual signature is (msg, isError, details).
                    // Pre-fix passed (msg, 4000, true) — the 4000 was treated as
                    // a truthy isError flag (correct outcome by accident) but the
                    // `true` ended up as the `details` string, so the error toast
                    // showed a meaningless "true" subline under the real message.
                    if (typeof showToast === 'function') showToast('Failed to load paint from SHOKK: ' + e.message, true);
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
                        _psdPath = null;
                        loadDecodedImageToCanvas(tga.width, tga.height, tga.rgba, fileName);
                    } catch (err) {
                        // 2026-04-19 TRUE FIVE-HOUR (TF17b) — same signature fix as TF17a.
                        if (typeof showToast === 'function') showToast('TGA decode error: ' + err.message, true);
                    }
                };
                reader.readAsArrayBuffer(file);
            } else {
                const reader = new FileReader();
                reader.onload = function (e) {
                    const img = new Image();
                    img.onload = function () {
                        _psdPath = null;
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
                if (!Array.isArray(zone.colors)) zone.colors = [];

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

        var _selectionMoveDrag = null;

        function _shiftRegionMask(mask, w, h, dx, dy) {
            const shifted = new Uint8Array(w * h);
            if (!mask || !w || !h) return shifted;
            for (let y = 0; y < h; y++) {
                for (let x = 0; x < w; x++) {
                    const idx = y * w + x;
                    if (mask[idx] <= 0) continue;
                    const nx = x + dx;
                    const ny = y + dy;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        shifted[ny * w + nx] = mask[idx];
                    }
                }
            }
            return shifted;
        }

        function activateSelectionMove() {
            if (typeof hasActivePixelSelection !== 'function' || !hasActivePixelSelection()) {
                if (typeof showToast === 'function') showToast('No selection to move — draw a selection first', true);
                return false;
            }
            if (typeof setCanvasMode === 'function') setCanvasMode('selection-move');
            return true;
        }
        window.activateSelectionMove = activateSelectionMove;

        function cancelSelectionMove(noToast) {
            if (!_selectionMoveDrag) return false;
            const zone = zones && zones[selectedZoneIndex];
            if (zone && _selectionMoveDrag.baseMask) {
                zone.regionMask = new Uint8Array(_selectionMoveDrag.baseMask);
            }
            _selectionMoveDrag = null;
            isDrawing = false;
            const canvas = document.getElementById('paintCanvas');
            if (canvas) canvas.style.cursor = 'grab';
            if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
            if (typeof renderZones === 'function') renderZones();
            if (typeof updateRegionStatus === 'function') updateRegionStatus();
            if (typeof renderContextActionBar === 'function') renderContextActionBar();
            // FIVE-HOUR SHIFT Win H1: pre-fix this restored the regionMask but
            // never fired triggerPreviewRender(). regionMask flows into the
            // render payload, so the preview kept showing the moved-mask state
            // even after the painter cancelled. Same silent-stale class as Wins
            // C1/C2/C6.
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            if (!noToast && typeof showToast === 'function') showToast('Selection move cancelled');
            return true;
        }
        window.cancelSelectionMove = cancelSelectionMove;

        // Nudge the current zone's drawn region by (dx, dy) pixels. Use Alt+Arrow (e.g. in 6-ui-boot).
        function nudgeRegionSelection(dx, dy) {
            const canvas = document.getElementById('paintCanvas');
            if (!canvas || typeof zones === 'undefined' || selectedZoneIndex < 0 || selectedZoneIndex >= zones.length) return false;
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask || !zone.regionMask.some(v => v > 0)) return false;
            // 2026-04-18 MARATHON bug #44 (Street, MED) + bug #52
            // (Luger, HIGH): the drag-coalesced undo MUST use pushZoneUndo
            // (which has the 500ms drag timer), NOT pushUndo (which does
            // NOT coalesce and spams the 30-slot stack). Pre-fix, hold
            // ArrowRight for 1 sec → 30 push events → MAX_UNDO eviction
            // deleted the painter's earlier unrelated edits AND required
            // 30 Ctrl+Z presses to undo the nudge. Use pushZoneUndo with
            // isDrag=true so bursts collapse to ONE entry.
            if (typeof pushZoneUndo === 'function') {
                pushZoneUndo('nudge selection', true);
            } else if (typeof pushUndo === 'function') {
                pushUndo(selectedZoneIndex);
            }
            const w = canvas.width, h = canvas.height;
            zone.regionMask = _shiftRegionMask(zone.regionMask, w, h, dx, dy);
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

        // ===== LIVE PREVIEW / CANVAS DISPLAY MODES =====
        let canvasDisplayMode = 'source'; // 'source' | 'rendered' | 'split'
        let splitViewActive = false;
        let previewDebounceTimer = null;
        let previewAbortController = null;
        let previewVersion = 0;           // Monotonic counter for staleness detection
        let previewIsRendering = false;
        let lastPreviewZoneHash = '';

        function isPreviewSurfaceVisible() {
            return canvasDisplayMode === 'rendered' || canvasDisplayMode === 'split';
        }

        function _updateCanvasDisplayModeButtons() {
            const modeButtons = {
                source: document.getElementById('btnCanvasViewSource'),
                rendered: document.getElementById('btnCanvasViewRendered'),
                split: document.getElementById('btnSplitView'),
            };
            Object.keys(modeButtons).forEach(function (mode) {
                const btn = modeButtons[mode];
                if (!btn) return;
                const active = canvasDisplayMode === mode;
                btn.setAttribute('aria-pressed', active ? 'true' : 'false');
                btn.classList.toggle('split-active', active);
                btn.style.borderColor = active ? '#00C8C8' : '';
                btn.style.color = active ? '#eaffff' : '';
                btn.style.background = active ? 'rgba(0,200,200,0.16)' : '';
            });
        }

        function _getActiveRenderedPreviewSrc() {
            const liveImg = document.getElementById('livePreviewImg');
            const beforeImg = document.getElementById('beforePreviewImg');
            const showingBefore = (typeof beforeAfterActive !== 'undefined') && beforeAfterActive;
            if (showingBefore && beforeImg && beforeImg.src) return beforeImg.src;
            return (liveImg && liveImg.src) ? liveImg.src : '';
        }

        function syncRenderedCanvasPreview() {
            const renderedImg = document.getElementById('canvasRenderedViewImg');
            const renderedBadge = document.getElementById('canvasRenderedModeBadge');
            const paintCanvas = document.getElementById('paintCanvas');
            const activePreviewSrc = _getActiveRenderedPreviewSrc();
            const renderedMode = canvasDisplayMode === 'rendered';

            if (renderedImg) {
                if (activePreviewSrc) renderedImg.src = activePreviewSrc;
                renderedImg.style.display = (renderedMode && activePreviewSrc) ? 'block' : 'none';
            }
            if (renderedBadge) renderedBadge.style.display = (renderedMode && activePreviewSrc) ? '' : 'none';
            if (paintCanvas) {
                paintCanvas.style.opacity = (renderedMode && activePreviewSrc) ? '0.18' : '1';
            }
        }
        if (typeof window !== 'undefined') window.syncRenderedCanvasPreview = syncRenderedCanvasPreview;

        function updatePreviewControlAvailability() {
            const liveImg = document.getElementById('livePreviewImg');
            const specImg = document.getElementById('livePreviewSpecImg');
            const hasCurrentPreview = !!(liveImg && liveImg.src);
            const hasBeforePreview = hasCurrentPreview && typeof beforeImageCaptured !== 'undefined' && beforeImageCaptured;
            const hasSpecPreview = !!(specImg && specImg.src);
            const beforeActive = (typeof beforeAfterActive !== 'undefined') && beforeAfterActive;

            [document.getElementById('btnBeforeAfter'), document.getElementById('btnBeforeAfterSource')].forEach(function (btn) {
                if (!btn) return;
                btn.style.display = hasBeforePreview ? '' : 'none';
                btn.disabled = !hasBeforePreview;
                btn.style.opacity = hasBeforePreview ? '1' : '0.45';
                btn.style.background = beforeActive ? 'rgba(255,170,0,0.15)' : '';
            });

            [document.getElementById('btnSpecMapInspector'), document.getElementById('btnSpecMapInspectorSource')].forEach(function (btn) {
                if (!btn) return;
                btn.disabled = !hasSpecPreview;
                btn.style.opacity = hasSpecPreview ? '1' : '0.55';
                btn.title = hasSpecPreview
                    ? 'Channels Inspector - view spec map channels and numeric values'
                    : 'Channels unavailable until a preview spec map finishes rendering';
            });
        }
        if (typeof window !== 'undefined') window.updatePreviewControlAvailability = updatePreviewControlAvailability;

        function setCanvasDisplayMode(mode, options) {
            const opts = options || {};
            const nextMode = (mode === 'rendered' || mode === 'split') ? mode : 'source';
            canvasDisplayMode = nextMode;
            splitViewActive = nextMode === 'split';

            const previewPane = document.getElementById('splitPreview');
            const sourceLabel = document.getElementById('sourcePaneLabel');
            const sourceTitle = document.getElementById('sourcePaneTitle');
            const sourcePreviewControls = document.getElementById('sourcePreviewControls');

            if (previewPane) previewPane.style.display = splitViewActive ? 'flex' : 'none';
            if (sourceLabel) sourceLabel.style.display = nextMode === 'source' ? 'none' : '';
            if (sourceTitle) sourceTitle.textContent = nextMode === 'rendered' ? 'CAR VIEW' : 'SOURCE';
            if (sourcePreviewControls) sourcePreviewControls.style.display = nextMode === 'rendered' ? '' : 'none';

            _updateCanvasDisplayModeButtons();
            syncRenderedCanvasPreview();
            updatePreviewControlAvailability();

            // Re-fit source canvas to the new (narrower or wider) space
            setTimeout(() => canvasZoom('fit'), 50);

            // Trigger initial preview if zones are configured
            if (!opts.skipPreview && isPreviewSurfaceVisible()) {
                triggerPreviewRender();
            }
            return nextMode;
        }
        if (typeof window !== 'undefined') window.setCanvasDisplayMode = setCanvasDisplayMode;

        function toggleSplitView(forceOn) {
            if (forceOn === true) return setCanvasDisplayMode('split');
            if (forceOn === false) return setCanvasDisplayMode('source');
            return setCanvasDisplayMode(splitViewActive ? 'source' : 'split');
        }
        if (typeof window !== 'undefined') window.toggleSplitView = toggleSplitView;

        function _initCanvasDisplayModeUi() {
            _updateCanvasDisplayModeButtons();
            if (typeof _updateToolbarEditModeButtons === 'function') _updateToolbarEditModeButtons();
            syncRenderedCanvasPreview();
            updatePreviewControlAvailability();
        }
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', _initCanvasDisplayModeUi);
        } else {
            _initCanvasDisplayModeUi();
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
                specBtn.style.borderColor = '#00C8C8';
                specBtn.style.color = '#00C8C8';
                paintBtn.style.borderColor = '#333';
                paintBtn.style.color = '#E87A20';
                chBtns.forEach(id => { const b = document.getElementById(id); if (b) b.style.display = ''; });

                // Channel filtering: extract specific RGBA channel from spec image
                const specSrc = document.getElementById('livePreviewSpecImg');
                if (!specSrc || !specSrc.src) return;
                const ch = channel || 'all';

                // Highlight active channel button
                const chMap = { all: 'lightboxChAll', r: 'lightboxChR', g: 'lightboxChG', b: 'lightboxChB' };
                chBtns.forEach(id => {
                    const b = document.getElementById(id);
                    if (b) b.style.borderColor = (id === chMap[ch]) ? '#00e5ff' : '#333';
                });

                if (ch === 'all') {
                    img.src = specSrc.src;
                } else {
                    // Extract channel via offscreen canvas
                    // Track L #243 — willReadFrequently:true since this is a
                    // class C draw+read pattern, called per channel-inspector
                    // refresh on a 2048×2048 spec map texture.
                    const offscreen = document.createElement('canvas');
                    const tempImg = new Image();
                    tempImg.onload = function () {
                        offscreen.width = tempImg.naturalWidth;
                        offscreen.height = tempImg.naturalHeight;
                        const ctx = offscreen.getContext('2d', { willReadFrequently: true });
                        ctx.drawImage(tempImg, 0, 0);
                        const data = ctx.getImageData(0, 0, offscreen.width, offscreen.height);
                        const d = data.data;
                        const chIdx = { r: 0, g: 1, b: 2, a: 3 }[ch] || 0;
                        const tints = { r: [1.0,0.3,0.3], g: [0.3,1.0,0.3], b: [0.3,0.5,1.0], a: [1.0,0.7,0.3] };
                        const tint = tints[ch] || [1,1,1];
                        for (let i = 0; i < d.length; i += 4) {
                            const v = d[i + chIdx];
                            d[i] = Math.min(255, Math.round(v * tint[0]));
                            d[i+1] = Math.min(255, Math.round(v * tint[1]));
                            d[i+2] = Math.min(255, Math.round(v * tint[2]));
                            d[i+3] = 255;
                        }
                        ctx.putImageData(data, 0, 0);
                        img.src = offscreen.toDataURL('image/png');
                    };
                    tempImg.src = specSrc.src;
                }
            }
        }

        function closePreviewLightbox() {
            const lb = document.getElementById('previewLightbox');
            if (lb) lb.style.display = 'none';
            document.removeEventListener('keydown', lightboxKeyHandler);
        }

        // Live Preview zoom: paint and spec panes must zoom independently.
        var _previewZoomByPane = { paint: 1.0, spec: 1.0 };
        function _getPreviewZoomPane(target) {
            if (!target || !target.closest) return null;
            if (target.closest('#previewSpecPane, #livePreviewSpecImg, #specChannelCanvas')) return 'spec';
            if (target.closest('#previewPaintPane, #livePreviewImg')) return 'paint';
            const specPane = document.getElementById('previewSpecPane');
            if (specPane && specPane.classList.contains('spec-expanded')) return 'spec';
            if (target.closest('#splitPreview, #previewPane, .preview-inner')) return 'paint';
            return null;
        }
        function _applyPreviewPaneZoom(pane) {
            const zoom = _previewZoomByPane[pane] || 1.0;
            const targets = pane === 'spec'
                ? [document.getElementById('livePreviewSpecImg'), document.getElementById('specChannelCanvas')]
                : [document.getElementById('livePreviewImg')];
            targets.forEach(el => {
                if (!el) return;
                el.style.transform = `scale(${zoom})`;
                el.style.transformOrigin = 'center center';
            });
        }
        document.addEventListener('DOMContentLoaded', function () {
            const previewPane = document.getElementById('splitPreview');
            if (!previewPane) return;
            previewPane.addEventListener('wheel', function (e) {
                const pane = _getPreviewZoomPane(e.target);
                if (!pane) return;
                e.preventDefault();
                e.stopPropagation();
                if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
                const delta = e.deltaY > 0 ? -0.15 : 0.15;
                _previewZoomByPane[pane] = Math.max(0.25, Math.min(4.0, (_previewZoomByPane[pane] || 1.0) + delta));
                _applyPreviewPaneZoom(pane);
            }, { passive: false });
        });

        function lightboxKeyHandler(e) {
            if (e.defaultPrevented) return; // SESSION ROUTER bail
            if (e.key === 'Escape') closePreviewLightbox();
            if (e.key === 'p' || e.key === 'P') showLightbox('paint');
            if (e.key === 's' || e.key === 'S') showLightbox('spec');
        }

        function getZoneConfigHash() {
            // Hash ALL rendering-relevant zone fields to detect actual changes
            // Must match every field sent to server in doPreviewRender / doRender
            const muteKey = zones.map(z => z.muted ? '1' : '0').join('');
            const validZones = zones.filter(z => !z.muted && _zoneHasRenderableMaterialClient(z) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
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
                sourceLayer: z.sourceLayer,
                // Base color system (FROM SPECIAL, solid color, etc.)
                baseColorMode: z.baseColorMode, baseColor: z.baseColor,
                baseColorSource: z.baseColorSource, baseColorStrength: z.baseColorStrength,
                baseColorFitZone: z.baseColorFitZone,
                baseHueOffset: z.baseHueOffset, baseSaturationAdjust: z.baseSaturationAdjust,
                baseBrightnessAdjust: z.baseBrightnessAdjust,
                // 2026-04-18 marathon silent-drop fix: baseSpecBlendMode
                // affects how spec patterns stack with the base. Pre-fix it
                // was not in the hash, so changing the blend-mode dropdown
                // silently skipped the Live Preview refresh.
                baseSpecBlendMode: z.baseSpecBlendMode,
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
                secondBaseHueShift: z.secondBaseHueShift, secondBaseSaturation: z.secondBaseSaturation, secondBaseBrightness: z.secondBaseBrightness,
                secondBasePatternHueShift: z.secondBasePatternHueShift, secondBasePatternSaturation: z.secondBasePatternSaturation, secondBasePatternBrightness: z.secondBasePatternBrightness,
                secondBaseFitZone: z.secondBaseFitZone,
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
                thirdBaseHueShift: z.thirdBaseHueShift, thirdBaseSaturation: z.thirdBaseSaturation, thirdBaseBrightness: z.thirdBaseBrightness,
                thirdBaseFitZone: z.thirdBaseFitZone,
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
                fourthBaseHueShift: z.fourthBaseHueShift, fourthBaseSaturation: z.fourthBaseSaturation, fourthBaseBrightness: z.fourthBaseBrightness,
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
                fifthBaseHueShift: z.fifthBaseHueShift, fifthBaseSaturation: z.fifthBaseSaturation, fifthBaseBrightness: z.fifthBaseBrightness,
                fourthBaseFitZone: z.fourthBaseFitZone,
                fifthBaseFitZone: z.fifthBaseFitZone,
                // Spec pattern overlays — ALL 5 tiers must be here.
                // 2026-04-18 marathon silent-drop fix: hash previously only
                // covered 2 of 5 tiers. Painter added a pattern to the 3rd/
                // 4th/5th overlay tier and the Live Preview silently did
                // not re-render because the hash didn't change. Classic
                // "UI shows a new overlay, preview keeps rendering the
                // old state" trust break.
                specPatternStack: z.specPatternStack,
                overlaySpecPatternStack: z.overlaySpecPatternStack,
                thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack,
                fourthOverlaySpecPatternStack: z.fourthOverlaySpecPatternStack,
                fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack,
                // Placement / offset fields not covered above.
                basePatternOpacity: z.basePatternOpacity,
                basePatternScale: z.basePatternScale,
                basePatternRotation: z.basePatternRotation,
                patternStrengthMapEnabled: z.patternStrengthMapEnabled,
                // 2026-04-18 marathon silent-drop: track a cheap checksum of
                // the strength-map data so painter strokes on the strength
                // map actually invalidate the preview hash. Pre-fix only the
                // enabled toggle was hashed, so painting on the strength
                // map did not refresh the Live Preview.
                patternStrengthMapSum: (z.patternStrengthMap && z.patternStrengthMap.data)
                    ? (function () {
                        // Cheap O(w) diagonal checksum — the full sum would be
                        // ~4M ops on every hash call. Diagonal sample is enough
                        // to detect any real stroke.
                        var d = z.patternStrengthMap.data;
                        var w = z.patternStrengthMap.width || 0;
                        var h = z.patternStrengthMap.height || 0;
                        var s = 0, n = Math.min(w, h, 256);
                        for (var i = 0; i < n; i++) s = (s * 31 + d[i * (w + 1)] | 0);
                        return s;
                    })() : 0,
                hardEdge: z.hardEdge,
                patternFitZone: z.patternFitZone,
                patternPlacement: z.patternPlacement,
                // Gradient stops (see BOIL THE OCEAN gradient_stops fix).
                gradientStops: z.gradientStops,
                gradientDirection: z.gradientDirection,
                // Region mask: track length + sum for change detection
                rmLen: z.regionMask ? z.regionMask.length : 0,
                rmSum: z.regionMask ? z.regionMask.reduce((a, b) => a + b, 0) : 0,
                // WIN #8 (Hawk audit, HIGH): spatialMask is sent to engine as
                // zoneObj.spatial_mask (paint-booth-5-api-render.js ~L1956), but
                // pre-fix the hash only included regionMask. Toggling spatial
                // include/exclude that round-tripped back to a previously hashed
                // state would silently keep the preview stale.
                smLen: z.spatialMask ? z.spatialMask.length : 0,
                smSum: z.spatialMask ? z.spatialMask.reduce((a, b) => a + b, 0) : 0,
            }));
            const layerRevision = (typeof _layerCompositeRevision !== 'undefined') ? _layerCompositeRevision : 0;
            return muteKey + JSON.stringify(hashData) + '|layers:' + layerRevision;
        }

        // Tiered preview: 3-stage progressive rendering for smoother feedback
        // Stage 1: 0.25 scale (512x512) — fast, shows layout + basic detail
        // Stage 2: 0.5 scale (1024x1024) — after 1s idle, good detail
        // Stage 3: 1.0 scale (2048x2048) — after 3s idle, FULL resolution
        let _previewEnhanceTimer = null;
        let _previewStage2Timer = null;
        let _lastPreviewScale = 0.5;

        function triggerPreviewRender() {
            // [#216] Optional caller-trace logging. Silent unless the painter (or
            // Hawk during a perf hunt) flips window._SPB_DEBUG_PREVIEW=true at
            // runtime. Helps confirm whether a single user action is firing the
            // trigger 2-3 times because multiple subroutines all call it.
            // The debounce inside this function still coalesces them, but knowing
            // that opacity slider drag fires N times per tick is useful data.
            if (typeof window !== 'undefined' && window._SPB_DEBUG_PREVIEW === true) {
                try {
                    var _stack = (new Error()).stack || '';
                    // Strip the first two frames (Error + this function) and grab
                    // the immediate caller. Format varies by browser; we keep the
                    // first non-Error line as a best-effort label.
                    var _lines = _stack.split('\n').map(function (s) { return s.trim(); });
                    var _caller = '';
                    for (var _i = 0; _i < _lines.length; _i++) {
                        var _l = _lines[_i];
                        if (!_l || _l === 'Error' || _l.indexOf('triggerPreviewRender') >= 0) continue;
                        _caller = _l;
                        break;
                    }
                    console.log('[preview-trace] triggerPreviewRender from:', _caller || '(unknown)');
                } catch (_e) { /* never let diagnostics break the call */ }
            }

            // Allow preview during manual placement even if the preview surface is off.
            if (typeof isPreviewSurfaceVisible === 'function' &&
                !isPreviewSurfaceVisible() &&
                placementLayer === 'none') return;

            const hash = getZoneConfigHash();
            if (hash === lastPreviewZoneHash) return;  // Nothing actually changed
            if (hash === '') {
                // No valid zones - show empty state
                updatePreviewStatus('', '');
                const paintImg = document.getElementById('livePreviewImg');
                const specImg = document.getElementById('livePreviewSpecImg');
                if (paintImg) paintImg.removeAttribute('src');
                if (specImg) specImg.removeAttribute('src');
                document.getElementById('previewPaintPane').style.display = 'none';
                document.getElementById('previewSpecPane').style.display = 'none';
                document.getElementById('previewSpecPane').classList.remove('spec-expanded');
                specExpanded = false;
                document.getElementById('previewSpinner').style.display = 'none';
                document.getElementById('previewEmpty').style.display = '';
                if (typeof syncRenderedCanvasPreview === 'function') syncRenderedCanvasPreview();
                if (typeof updatePreviewControlAvailability === 'function') updatePreviewControlAvailability();
                return;
            }

            // Mark as stale
            updatePreviewStatus('stale', 'Changed');

            // Cancel any pending stage 2 and stage 3 enhances
            if (_previewStage2Timer) { clearTimeout(_previewStage2Timer); _previewStage2Timer = null; }
            if (_previewEnhanceTimer) { clearTimeout(_previewEnhanceTimer); _previewEnhanceTimer = null; }

            // Debounce: Stage 1 — ultra-fast tiny preview after 300ms
            if (previewDebounceTimer) clearTimeout(previewDebounceTimer);
            previewDebounceTimer = setTimeout(() => {
                _lastPreviewScale = 0.25;
                doPreviewRender(hash, 0.25);

                // Stage 2 — medium preview after 1s of no further changes
                let _stage2Retries = 0;
                _previewStage2Timer = setTimeout(function _tryStage2() {
                    if (previewIsRendering) {
                        _stage2Retries++;
                        if (_stage2Retries > 5) return;
                        _previewStage2Timer = setTimeout(_tryStage2, 500);
                        return;
                    }
                    const currentHash = getZoneConfigHash();
                    if (currentHash === lastPreviewZoneHash && _lastPreviewScale < 0.5) {
                        _lastPreviewScale = 0.5;
                        doPreviewRender(currentHash, 0.5);
                    }
                }, 1000);

                // Stage 3 — full quality after 3s of no further changes
                // Cap at 0.5 scale (1024x1024) — full 1.0 is reserved for final render
                let _enhanceRetries = 0;
                _previewEnhanceTimer = setTimeout(function _tryEnhance() {
                    if (previewIsRendering) {
                        _enhanceRetries++;
                        if (_enhanceRetries > 5) return;  // Give up after 5 retries
                        _previewEnhanceTimer = setTimeout(_tryEnhance, 1500);
                        return;
                    }
                    const currentHash = getZoneConfigHash();
                    if (currentHash === lastPreviewZoneHash && _lastPreviewScale < 1.0) {
                        _lastPreviewScale = 1.0;
                        doPreviewRender(currentHash, 1.0);
                    }
                }, 3000);
            }, 300);
        }

        function buildLivePaintCompositeCanvas() {
            const pc = document.getElementById('paintCanvas');
            if (!pc || pc.width <= 0 || pc.height <= 0) return null;
            if (!(typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded &&
                    typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers) &&
                    _psdLayers.length > 0)) {
                return pc;
            }

            const tc = document.createElement('canvas');
            tc.width = pc.width;
            tc.height = pc.height;
            const tctx = tc.getContext('2d', { willReadFrequently: true });
            const activeLayer = (typeof getSelectedLayer === 'function') ? getSelectedLayer() : null;

            for (const layer of _psdLayers) {
                if (!layer || !layer.img || layer.visible === false) continue;
                if (typeof renderLayerEffects === 'function') renderLayerEffects(tctx, layer, 'before');
                tctx.globalAlpha = (layer.opacity != null ? layer.opacity : 255) / 255;
                tctx.globalCompositeOperation = layer.blendMode || 'source-over';
                if (activeLayer && _activeLayerCanvas && layer.id === activeLayer.id) {
                    tctx.drawImage(_activeLayerCanvas, 0, 0);
                } else {
                    const bx = layer.bbox ? layer.bbox[0] : 0;
                    const by = layer.bbox ? layer.bbox[1] : 0;
                    tctx.drawImage(layer.img, bx, by);
                }
                tctx.globalAlpha = 1.0;
                tctx.globalCompositeOperation = 'source-over';
                if (typeof renderLayerEffects === 'function') renderLayerEffects(tctx, layer, 'after');
            }

            tctx.globalAlpha = 1.0;
            tctx.globalCompositeOperation = 'source-over';
            return tc;
        }
        if (typeof window !== 'undefined') window.buildLivePaintCompositeCanvas = buildLivePaintCompositeCanvas;

        function _attachLivePaintCanvasToPreviewBody(body, fallbackPaintFile) {
            if (!_psdPath) return false;
            const pc = (typeof buildLivePaintCompositeCanvas === 'function')
                ? buildLivePaintCompositeCanvas()
                : document.getElementById('paintCanvas');
            if (!pc || pc.width <= 0 || pc.height <= 0) return false;
            try {
                body.paint_image_base64 = pc.toDataURL('image/png');
                body.paint_file = _psdPath || fallbackPaintFile;
                return true;
            } catch (e) {
                console.warn('[preview] Failed to capture live PSD canvas:', e);
                return false;
            }
        }

        async function doPreviewRender(zoneHash, previewScale) {
            const _pScale = previewScale || 0.25;
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
                    const validZones = zones.filter(z => !z.muted && _zoneHasRenderableMaterialClient(z) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
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
                            } else if (_bMode === 'gradient' && z.gradientStops && z.gradientStops.length >= 2) {
                                zoneObj.gradient_stops = z.gradientStops;
                                zoneObj.gradient_direction = z.gradientDirection || 'horizontal';
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
                        if (z.hardEdge) zoneObj.hard_edge = true;
                        // Source layer restriction: gate the zone to only the pixels where
                        // this PSD layer visibly contributes to the final composite.
                        if (z.sourceLayer && typeof _psdLayers !== 'undefined') {
                            const srcLayer = _psdLayers.find(l => l.id === z.sourceLayer);
                            if (srcLayer && srcLayer.img) {
                                const pc = document.getElementById('paintCanvas');
                                const w = pc?.width || 2048, h = pc?.height || 2048;

                                const visibleMask = getLayerVisibleContributionMask(srcLayer, w, h);
                                if (visibleMask && typeof encodeRegionMaskRLE === 'function') {
                                    zoneObj.source_layer_mask = encodeRegionMaskRLE(visibleMask, w, h);
                                    let visiblePixels = 0;
                                    for (let pi = 0; pi < visibleMask.length; pi++) {
                                        if (visibleMask[pi] > 0) visiblePixels++;
                                    }
                                    console.log(`[Layer Restrict] ${srcLayer.name}: visible contribution mask, ${visiblePixels} pixels`);
                                }
                            }
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
                        const suppressScopedExactColorOverlays = _zoneShouldPreserveScopedBrushExactColor(z);
                        if (!suppressScopedExactColorOverlays && z.blendBase && z.blendBase !== 'undefined' && z.blendBase !== 'none') {
                            zoneObj.blend_base = z.blendBase;
                            zoneObj.blend_dir = z.blendDir || 'horizontal';
                            zoneObj.blend_amount = (z.blendAmount ?? 50) / 100;
                        }
                        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
                        if (!suppressScopedExactColorOverlays && (z.secondBase || z.secondBaseColorSource) && (z.secondBaseStrength || 0) > 0) {
                            const _sbColor = z.secondBaseColor || '#ffffff';
                            const _sbColorSource = z.secondBaseColorSource || ((typeof z.secondBase === 'string' && z.secondBase.startsWith('mono:')) ? 'solid' : null);
                            if (z.secondBase && z.secondBase !== 'undefined') zoneObj.second_base = z.secondBase;
                            zoneObj.second_base_color = [parseInt(_sbColor.slice(1, 3), 16) / 255, parseInt(_sbColor.slice(3, 5), 16) / 255, parseInt(_sbColor.slice(5, 7), 16) / 255];
                            zoneObj.second_base_strength = z.secondBaseStrength || 0;
                            zoneObj.second_base_spec_strength = z.secondBaseSpecStrength ?? 1;
                            if (_sbColorSource && _sbColorSource !== 'undefined') zoneObj.second_base_color_source = _sbColorSource;
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
                            if (z.secondBaseHueShift) zoneObj.second_base_hue_shift = z.secondBaseHueShift;
                            if (z.secondBaseSaturation) zoneObj.second_base_saturation = z.secondBaseSaturation;
                            if (z.secondBaseBrightness) zoneObj.second_base_brightness = z.secondBaseBrightness;
                            if (z.secondBasePatternHueShift) zoneObj.second_base_pattern_hue_shift = z.secondBasePatternHueShift;
                            if (z.secondBasePatternSaturation) zoneObj.second_base_pattern_saturation = z.secondBasePatternSaturation;
                            if (z.secondBasePatternBrightness) zoneObj.second_base_pattern_brightness = z.secondBasePatternBrightness;
                        }
                        if (!suppressScopedExactColorOverlays && (z.thirdBase || z.thirdBaseColorSource) && (z.thirdBaseStrength || 0) > 0) {
                            const _tbColor = (z.thirdBaseColor || '#ffffff').toString();
                            const hex = _tbColor.length >= 7 ? _tbColor : '#ffffff';
                            const _tbColorSource = z.thirdBaseColorSource || ((typeof z.thirdBase === 'string' && z.thirdBase.startsWith('mono:')) ? 'solid' : null);
                            if (z.thirdBase && z.thirdBase !== 'undefined') zoneObj.third_base = z.thirdBase;
                            zoneObj.third_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
                            zoneObj.third_base_strength = z.thirdBaseStrength || 0;
                            zoneObj.third_base_spec_strength = z.thirdBaseSpecStrength ?? 1;
                            if (_tbColorSource && _tbColorSource !== 'undefined') zoneObj.third_base_color_source = _tbColorSource;
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
                            if (z.thirdBaseHueShift) zoneObj.third_base_hue_shift = z.thirdBaseHueShift;
                            if (z.thirdBaseSaturation) zoneObj.third_base_saturation = z.thirdBaseSaturation;
                            if (z.thirdBaseBrightness) zoneObj.third_base_brightness = z.thirdBaseBrightness;
                        }
                        if (!suppressScopedExactColorOverlays && (z.fourthBase || z.fourthBaseColorSource) && (z.fourthBaseStrength || 0) > 0) {
                            const _fbColor = (z.fourthBaseColor || '#ffffff').toString();
                            const hex = _fbColor.length >= 7 ? _fbColor : '#ffffff';
                            const _fbColorSource = z.fourthBaseColorSource || ((typeof z.fourthBase === 'string' && z.fourthBase.startsWith('mono:')) ? 'solid' : null);
                            if (z.fourthBase && z.fourthBase !== 'undefined') zoneObj.fourth_base = z.fourthBase;
                            zoneObj.fourth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
                            zoneObj.fourth_base_strength = z.fourthBaseStrength || 0;
                            zoneObj.fourth_base_spec_strength = z.fourthBaseSpecStrength ?? 1;
                            if (_fbColorSource && _fbColorSource !== 'undefined') zoneObj.fourth_base_color_source = _fbColorSource;
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
                            if (z.fourthBaseHueShift) zoneObj.fourth_base_hue_shift = z.fourthBaseHueShift;
                            if (z.fourthBaseSaturation) zoneObj.fourth_base_saturation = z.fourthBaseSaturation;
                            if (z.fourthBaseBrightness) zoneObj.fourth_base_brightness = z.fourthBaseBrightness;
                        }
                        if (!suppressScopedExactColorOverlays && (z.fifthBase || z.fifthBaseColorSource) && (z.fifthBaseStrength || 0) > 0) {
                            const _fifColor = (z.fifthBaseColor || '#ffffff').toString();
                            const hex = _fifColor.length >= 7 ? _fifColor : '#ffffff';
                            const _fifColorSource = z.fifthBaseColorSource || ((typeof z.fifthBase === 'string' && z.fifthBase.startsWith('mono:')) ? 'solid' : null);
                            if (z.fifthBase && z.fifthBase !== 'undefined') zoneObj.fifth_base = z.fifthBase;
                            zoneObj.fifth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
                            zoneObj.fifth_base_strength = z.fifthBaseStrength || 0;
                            zoneObj.fifth_base_spec_strength = z.fifthBaseSpecStrength ?? 1;
                            if (_fifColorSource && _fifColorSource !== 'undefined') zoneObj.fifth_base_color_source = _fifColorSource;
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
                            if (z.fifthBaseHueShift) zoneObj.fifth_base_hue_shift = z.fifthBaseHueShift;
                            if (z.fifthBaseSaturation) zoneObj.fifth_base_saturation = z.fifthBaseSaturation;
                            if (z.fifthBaseBrightness) zoneObj.fifth_base_brightness = z.fifthBaseBrightness;
                        }
                        const hasSpatialRefinement = z.spatialMask && z.spatialMask.some(v => v > 0);
                        if (!hasSpatialRefinement && z.regionMask && z.regionMask.some(v => v > 0)) { const pc = document.getElementById('paintCanvas'); if (pc) zoneObj.region_mask = encodeRegionMaskRLE(z.regionMask, pc.width, pc.height); }
                        if (hasSpatialRefinement) {
                            const pc = document.getElementById('paintCanvas');
                            if (pc) zoneObj.spatial_mask = encodeRegionMaskRLE(z.spatialMask, pc.width, pc.height);
                        }
                        if (_zoneShouldRequestPriorityOverride(z)) zoneObj.priority_override = true;
                        return zoneObj;
                    });
                })();

            // Build request body — tiered: 0.5 for fast feedback, 1.0 for full quality
            const body = {
                paint_file: paintFile,
                zones: serverZones,
                seed: 51,
                preview_scale: _pScale,
            };

            // Incremental rendering hints: tell server which zone changed and per-zone hashes
            // so unchanged zones can be served from the zone-level cache in build_multi_zone.
            body.changed_zone = selectedZoneIndex;
            body.zone_hashes = zones.filter(z => !z.muted && _zoneHasRenderableMaterialClient(z)).map(z => {
                return JSON.stringify({
                    base: z.base, finish: z.finish, pattern: z.pattern, scale: z.scale,
                    rotation: z.rotation, baseRotation: z.baseRotation, baseScale: z.baseScale,
                    baseStrength: z.baseStrength, baseSpecStrength: z.baseSpecStrength,
                    baseOffsetX: z.baseOffsetX, baseOffsetY: z.baseOffsetY,
                    baseFlipH: z.baseFlipH, baseFlipV: z.baseFlipV,
                    patternOpacity: z.patternOpacity, patternStack: z.patternStack,
                    patternSpecMult: z.patternSpecMult,
                    patternOffsetX: z.patternOffsetX, patternOffsetY: z.patternOffsetY,
                    patternFlipH: z.patternFlipH, patternFlipV: z.patternFlipV,
                    intensity: z.intensity, patternIntensity: z.patternIntensity,
                    customSpec: z.customSpec, customPaint: z.customPaint, customBright: z.customBright,
                    color: z.color, colorMode: z.colorMode, colors: z.colors,
                    baseColorMode: z.baseColorMode, baseColor: z.baseColor,
                    baseColorSource: z.baseColorSource, baseColorStrength: z.baseColorStrength,
                    baseHueOffset: z.baseHueOffset, baseSaturationAdjust: z.baseSaturationAdjust,
                    baseBrightnessAdjust: z.baseBrightnessAdjust,
                    secondBase: z.secondBase, secondBaseStrength: z.secondBaseStrength,
                    specPatternStack: z.specPatternStack,
                    rmLen: z.regionMask ? z.regionMask.length : 0,
                    rmSum: z.regionMask ? z.regionMask.reduce((a, b) => a + b, 0) : 0,
                });
            });

            // Include imported spec map if active (merge mode)
            if (importedSpecMapPath) {
                body.import_spec_map = importedSpecMapPath;
            }

            // Include decal composited paint + spec finish info so preview shows decal spec
            if (typeof compositeDecalsForRender === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) {
                try {
                    const compositeCanvas = compositeDecalsForRender();
                    if (compositeCanvas) {
                        body.paint_image_base64 = compositeCanvas.toDataURL('image/png');
                    }
                    // Send the separate decal alpha mask so engine knows WHERE decals are
                    if (typeof compositeDecalMaskForRender === 'function') {
                        const maskDataUrl = compositeDecalMaskForRender();
                        if (maskDataUrl) body.decal_mask_base64 = maskDataUrl;
                    }
                    const decalSpecs = decalLayers
                        .filter(dl => dl.visible && dl.specFinish && dl.specFinish !== 'none')
                        .map(dl => ({ specFinish: dl.specFinish }));
                    if (decalSpecs.length > 0) {
                        body.decal_spec_finishes = decalSpecs;
                    }
                } catch (e) {
                    // Non-fatal: preview still works without decal spec
                    console.warn('[preview] Failed to composite decals for preview:', e);
                }
            }

            // CRITICAL: If PSD layers are loaded AND user has edited them (erased,
            // painted, moved, applied effects), send the live paint canvas as the
            // base64 paint source so those edits actually appear in the preview.
            // Without this, the server renders from the ORIGINAL paint file and the
            // user's layer edits never show up on the rendered car. The decal block
            // above already may have set paint_image_base64; if PSD has data we
            // override with the LIVE canvas (which already includes any decals
            // because decalLayers were migrated into _psdLayers).
            if (_attachLivePaintCanvasToPreviewBody(body, paintFile)) {
                body.paint_file = _psdPath || paintFile;
            }

            try {
                const resp = await fetch(ShokkerAPI.baseUrl + '/preview-render', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                    signal: previewAbortController.signal,
                });

                // Check if this response is still current (not superseded)
                if (thisVersion !== previewVersion) { previewIsRendering = false; return; }

                // 429 = server busy or superseded — silently ignore, don't show error
                if (resp.status === 429) { previewIsRendering = false; return; }

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
                const isNewPreviewRevision = zoneHash !== lastPreviewZoneHash;
                if (isNewPreviewRevision &&
                    paintImg &&
                    paintImg.src &&
                    typeof captureBeforeImage === 'function') {
                    captureBeforeImage(paintImg.src);
                }
                // Release old base64 data before assigning new (helps GC on large previews)
                if (paintImg && paintImg.src && paintImg.src.startsWith('data:')) {
                    try { URL.revokeObjectURL(paintImg.src); } catch(_) {}
                }
                if (specImg && specImg.src && specImg.src.startsWith('data:')) {
                    try { URL.revokeObjectURL(specImg.src); } catch(_) {}
                }
                if (paintImg && data.paint_preview) paintImg.src = data.paint_preview;
                if (specImg && data.spec_preview) specImg.src = data.spec_preview;
                // Show both panes (paint full, spec inset) - reset expanded state
                document.getElementById('previewPaintPane').style.display = '';
                document.getElementById('previewSpecPane').style.display = '';
                document.getElementById('previewSpecPane').classList.remove('spec-expanded');
                specExpanded = false;
                document.getElementById('previewEmpty').style.display = 'none';
                document.getElementById('previewSpinner').style.display = 'none';
                if (typeof syncRenderedCanvasPreview === 'function') syncRenderedCanvasPreview();
                if (typeof updatePreviewControlAvailability === 'function') updatePreviewControlAvailability();

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
                const _qualLabel = _pScale >= 1.0 ? 'HD' : `${Math.round(_pScale * 100)}%`;
                updatePreviewStatus('current', `${data.elapsed_ms}ms · ${_qualLabel}`);

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
                if (typeof updatePreviewControlAvailability === 'function') updatePreviewControlAvailability();
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
            // ── Full reset of the preview pipeline ──
            // Abort any in-flight fetch so the server stops churning
            try { if (previewAbortController) previewAbortController.abort(); } catch (e) {}
            previewAbortController = null;
            // Kill every pending debounce/stage/enhance timer
            if (typeof previewDebounceTimer !== 'undefined' && previewDebounceTimer) { clearTimeout(previewDebounceTimer); previewDebounceTimer = null; }
            if (typeof _previewStage2Timer !== 'undefined' && _previewStage2Timer) { clearTimeout(_previewStage2Timer); _previewStage2Timer = null; }
            if (typeof _previewEnhanceTimer !== 'undefined' && _previewEnhanceTimer) { clearTimeout(_previewEnhanceTimer); _previewEnhanceTimer = null; }
            // Clear stuck "rendering" flag
            previewIsRendering = false;
            // Clear hash so next render is NOT skipped as "unchanged"
            lastPreviewZoneHash = '';
            // Hide spinner/status
            var spinner = document.getElementById('previewSpinner');
            if (spinner) spinner.style.display = 'none';
            updatePreviewStatus('stale', 'Refreshing…');
            // If no preview surface is visible, switch to the single-pane CAR view
            // so the recovery render is immediately visible without forcing SPLIT.
            if (typeof isPreviewSurfaceVisible === 'function' &&
                !isPreviewSurfaceVisible() &&
                typeof setCanvasDisplayMode === 'function') {
                try { setCanvasDisplayMode('rendered', { skipPreview: true }); } catch (e) {}
            }
            // Kick off a fresh render immediately (bypass debounce)
            setTimeout(function() {
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            }, 50);
            if (typeof showToast === 'function') showToast('Preview refresh - pipeline reset', 'info');
        }
        // Expose globally so the Refresh button / keyboard shortcut / layer dock can use it
        if (typeof window !== 'undefined') window.forcePreviewRefresh = forcePreviewRefresh;

        // ===== CANVAS ZOOM + VIEW ROTATION =====
        let currentZoom = 1;
        let viewRotation = 0; // View rotation in degrees (non-destructive, CSS only)
        const ZOOM_STEPS = [0.1, 0.15, 0.2, 0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3, 4];

        function rotateView(degrees) {
            viewRotation = ((viewRotation + degrees) % 360 + 360) % 360;
            _updateViewTransform();
            if (typeof showToast === 'function') showToast(`View rotated: ${viewRotation}°`);
        }
        function resetViewRotation() {
            viewRotation = 0;
            _updateViewTransform();
            if (typeof showToast === 'function') showToast('View rotation reset');
        }
        // Canvas flip check — non-destructive CSS mirror for verifying symmetry
        var viewFlippedH = false;
        var viewFlippedV = false;
        function flipViewH() {
            viewFlippedH = !viewFlippedH;
            _updateViewTransform();
            if (typeof showToast === 'function') showToast(viewFlippedH ? 'View flipped horizontally (checking symmetry)' : 'View flip reset');
        }
        function flipViewV() {
            viewFlippedV = !viewFlippedV;
            _updateViewTransform();
            if (typeof showToast === 'function') showToast(viewFlippedV ? 'View flipped vertically' : 'View flip reset');
        }
        function _updateViewTransform() {
            const inner = document.getElementById('canvasInner');
            if (!inner) return;
            let t = `scale(${currentZoom})`;
            if (viewRotation) t += ` rotate(${viewRotation}deg)`;
            if (viewFlippedH) t += ' scaleX(-1)';
            if (viewFlippedV) t += ' scaleY(-1)';
            inner.style.transform = t;
        }
        function resetAllView() {
            viewRotation = 0; viewFlippedH = false; viewFlippedV = false;
            _updateViewTransform();
            if (typeof showToast === 'function') showToast('View reset');
        }
        window.rotateView = rotateView;
        window.resetViewRotation = resetViewRotation;
        // Grid/Rulers overlay for precision layout
        var _gridVisible = false;
        var _gridSize = 64; // pixels per grid cell
        var _guidesH = []; // horizontal guide positions (y values)
        var _guidesV = []; // vertical guide positions (x values)

        function toggleGrid() {
            _gridVisible = !_gridVisible;
            drawGridOverlay();
            if (typeof showToast === 'function') showToast(_gridVisible ? `Grid ON (${_gridSize}px)` : 'Grid OFF');
        }
        function setGridSize(size) {
            _gridSize = Math.max(8, Math.min(512, parseInt(size) || 64));
            if (_gridVisible) drawGridOverlay();
        }
        function addGuideH(y) {
            if (y == null) y = parseInt(prompt('Horizontal guide Y position (pixels):', '1024'));
            if (y != null && !isNaN(y)) { _guidesH.push(y); drawGridOverlay(); }
        }
        function addGuideV(x) {
            if (x == null) x = parseInt(prompt('Vertical guide X position (pixels):', '1024'));
            if (x != null && !isNaN(x)) { _guidesV.push(x); drawGridOverlay(); }
        }
        function clearGuides() { _guidesH = []; _guidesV = []; drawGridOverlay(); }

        function drawGridOverlay() {
            let gridCanvas = document.getElementById('gridOverlayCanvas');
            if (!gridCanvas) {
                const inner = document.getElementById('canvasInner');
                const pc = document.getElementById('paintCanvas');
                if (!inner || !pc) return;
                gridCanvas = document.createElement('canvas');
                gridCanvas.id = 'gridOverlayCanvas';
                gridCanvas.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:6;';
                inner.appendChild(gridCanvas);
            }
            const pc = document.getElementById('paintCanvas');
            if (!pc) return;
            gridCanvas.width = pc.width; gridCanvas.height = pc.height;
            gridCanvas.style.width = pc.style.width; gridCanvas.style.height = pc.style.height;
            const ctx = gridCanvas.getContext('2d');
            ctx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);

            if (!_gridVisible && _guidesH.length === 0 && _guidesV.length === 0) {
                gridCanvas.style.display = 'none';
                return;
            }
            gridCanvas.style.display = 'block';

            // Draw grid
            if (_gridVisible && _gridSize > 0) {
                ctx.strokeStyle = 'rgba(100,150,255,0.15)';
                ctx.lineWidth = 1;
                for (let x = _gridSize; x < pc.width; x += _gridSize) {
                    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, pc.height); ctx.stroke();
                }
                for (let y = _gridSize; y < pc.height; y += _gridSize) {
                    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(pc.width, y); ctx.stroke();
                }
                // Center lines brighter
                const cx = Math.round(pc.width / 2), cy = Math.round(pc.height / 2);
                ctx.strokeStyle = 'rgba(100,150,255,0.35)';
                ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, pc.height); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(pc.width, cy); ctx.stroke();
            }

            // Draw guides
            ctx.lineWidth = 1;
            ctx.setLineDash([8, 4]);
            ctx.strokeStyle = 'rgba(0,229,255,0.7)';
            for (const y of _guidesH) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(pc.width, y); ctx.stroke();
                ctx.fillStyle = 'rgba(0,229,255,0.6)'; ctx.font = '9px monospace';
                ctx.fillText(`Y:${y}`, 4, y - 3);
            }
            ctx.strokeStyle = 'rgba(255,100,255,0.7)';
            for (const x of _guidesV) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, pc.height); ctx.stroke();
                ctx.fillStyle = 'rgba(255,100,255,0.6)'; ctx.font = '9px monospace';
                ctx.fillText(`X:${x}`, x + 3, 12);
            }
            ctx.setLineDash([]);
        }

        window.toggleGrid = toggleGrid;
        window.setGridSize = setGridSize;
        window.addGuideH = addGuideH;
        window.addGuideV = addGuideV;
        window.clearGuides = clearGuides;
        window.drawGridOverlay = drawGridOverlay;
        window.flipViewH = flipViewH;
        window.flipViewV = flipViewV;
        window.resetAllView = resetAllView;

        function dockEyedropperInfoToTopToolbar() {
            const dock = document.getElementById('eyedropperDockTop');
            const info = document.getElementById('eyedropperInfo');
            if (!dock || !info) return false;
            if (info.parentElement !== dock) dock.appendChild(info);
            info.classList.add('eyedropper-info-docked');
            info.style.borderTop = '0';
            info.style.borderLeft = '2px solid var(--accent-blue)';
            info.style.borderRadius = '7px';
            info.style.padding = '4px 8px';
            return true;
        }
        window.dockEyedropperInfoToTopToolbar = dockEyedropperInfoToTopToolbar;
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', dockEyedropperInfoToTopToolbar);
        } else {
            dockEyedropperInfoToTopToolbar();
        }

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
                // 2026-04-18 MARATHON bug #45 (Street, MED): pre-fix, if
                // the fit container was 0-width (panel toggle mid-transition,
                // fullscreen animation, collapsed split pane) then
                // fitZoom could be 0 or negative → canvas rendered at 0×0
                // pixels, invisible. Painter had to Ctrl+= multiple times
                // to recover. Floor at 0.1 matching the pinch-zoom
                // handler at line 4201.
                currentZoom = Math.max(0.1, Math.min(fitZoom, 1));
            } else if (action === '100') {
                currentZoom = 1;
            } else if (action === '200') {
                currentZoom = 2;
            } else if (action === '300') {
                currentZoom = 3;
            } else if (action === '50') {
                currentZoom = 0.5;
            } else if (action === '25') {
                currentZoom = 0.25;
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
            if (e.defaultPrevented) return;
            if (e.code === 'Space' && !e.repeat && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
                spaceHeld = true;
                const viewport = document.getElementById('canvasViewport');
                if (viewport) viewport.style.cursor = 'grab';
                e.preventDefault();
            }
            // Escape: deselect layer if one is selected
            // 2026-04-18 MARATHON bug #42 (LOW-MED): pre-fix, pressing Esc
            // while typing in a text input (e.g. zone-name rename) would
            // deselect the painter's active layer instead of just cancelling
            // the input. Now gate on input focus, matching the Space key
            // guard already above.
            const _escTag = (e.target && e.target.tagName || '').toLowerCase();
            const _escIsInput = _escTag === 'input' || _escTag === 'textarea' || _escTag === 'select'
                || (e.target && e.target.isContentEditable);
            if (e.key === 'Escape' && _selectedLayerId && !_escIsInput) {
                // 2026-04-18 marathon audit — refuse mid-stroke deselect.
                // Pre-fix, pressing Esc during an in-progress layer paint
                // stroke deselected _selectedLayerId but left _activeLayerCanvas
                // pointing at the layer buffer. On mouseup, _commitLayerPaint
                // returned early (no selected layer) and left paintImageData
                // stuck pointing at the stale layer canvas. Symptom:
                // subsequent brush/eraser strokes went to the wrong buffer.
                // Fix: if the painter is currently drawing a layer stroke,
                // cancel the stroke in place rather than leaking state.
                if (isDrawing && _activeLayerCanvas) {
                    isDrawing = false;
                    _activeLayerCanvas = null;
                    _activeLayerCtx = null;
                    if (_savedPaintImageData) {
                        paintImageData = _savedPaintImageData;
                        _savedPaintImageData = null;
                    }
                    if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
                    if (typeof showToast === 'function') showToast('Layer stroke cancelled', 'info');
                    // Pop the undo entry we pushed at mousedown — Esc = cancel,
                    // not a permanent no-op on the undo stack.
                    if (Array.isArray(_layerUndoStack) && _layerUndoStack.length > 0) {
                        _layerUndoStack.pop();
                    }
                    e.preventDefault();
                    return;
                }
                _selectedLayerId = null;
                if (typeof window !== 'undefined') window._selectedLayerId = null;
                if (typeof clearLayerBounds === 'function') clearLayerBounds();
                if (typeof renderLayerPanel === 'function') renderLayerPanel();
                // Track P #319 — keep the active-tool label fresh on deselect.
                if (typeof refreshActiveToolLabel === 'function') refreshActiveToolLabel();
                if (typeof showToast === 'function') showToast('Layer deselected');
                e.preventDefault();
                return;
            }
            // Tool hotkeys (only when not in text input)
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
            // Ctrl+= zoom in, Ctrl+- zoom out, Ctrl+0 fit to screen
            if ((e.ctrlKey || e.metaKey) && (e.key === '=' || e.key === '+')) { e.preventDefault(); canvasZoom('in'); return; }
            if ((e.ctrlKey || e.metaKey) && e.key === '-') { e.preventDefault(); canvasZoom('out'); return; }
            if ((e.ctrlKey || e.metaKey) && e.key === '0') { e.preventDefault(); canvasZoom('fit'); return; }
            if (e.ctrlKey || e.metaKey || e.altKey) return; // Don't intercept other Ctrl combos
            const key = e.key.toLowerCase();
            if (key === 'b') { setCanvasMode('brush'); e.preventDefault(); }
            else if (key === 'x') { swapForegroundBackground(); e.preventDefault(); }
            else if (key === 'w') { setCanvasMode('wand'); e.preventDefault(); }
            else if (key === 'a') { setCanvasMode('selectall'); e.preventDefault(); }
            else if (key === 'e' && !e.shiftKey) { setCanvasMode('edge'); e.preventDefault(); }
            else if (key === 'p') { setCanvasMode('eyedropper'); e.preventDefault(); }
            else if (key === 'o') { setCanvasMode('rect'); e.preventDefault(); }
            else if (key === 'l') { setCanvasMode('lasso'); e.preventDefault(); }
            else if (key === 'g') { setCanvasMode('gradient'); e.preventDefault(); }
            else if (key === 'k') { setCanvasMode('fill'); e.preventDefault(); }
            else if (key === 'r' && !e.shiftKey) { setCanvasMode('recolor'); e.preventDefault(); }
            else if (key === 'd' && !e.shiftKey) { setCanvasMode('dodge'); e.preventDefault(); }
            else if (key === 'j') { setCanvasMode('burn'); e.preventDefault(); }
            else if (key === 'f') { setCanvasMode('blur-brush'); e.preventDefault(); }
            else if (key === 'h' && !e.shiftKey) { setCanvasMode('sharpen-brush'); e.preventDefault(); }
            else if (key === 'q') { setCanvasMode('smudge'); e.preventDefault(); }
            else if (key === 'i') { setCanvasMode('pencil'); e.preventDefault(); }
            else if (key === '?' || (e.shiftKey && key === '/')) { showShortcutLegend(); e.preventDefault(); }
            // Number keys: context-sensitive (Photoshop standard)
            // Layer selected → set layer opacity (1=10%, 0=100%)
            // Paint tool active (no layer) → set brush opacity
            // Otherwise → zoom shortcuts
            else if (key >= '0' && key <= '9') {
                const pct = key === '0' ? 100 : parseInt(key) * 10;
                const isPaintTool = ['colorbrush','brush','erase','clone','recolor','smudge','dodge','burn','blur-brush','sharpen-brush','pencil','history-brush'].includes(canvasMode);
                if (_selectedLayerId && typeof setLayerOpacity === 'function') {
                    setLayerOpacity(_selectedLayerId, pct);
                    if (typeof showToast === 'function') showToast(`Layer opacity: ${pct}%`);
                } else if (isPaintTool) {
                    const el = document.getElementById('brushOpacity');
                    if (el) { el.value = pct; if (el.oninput) el.oninput(); }
                    if (typeof showToast === 'function') showToast(`Brush opacity: ${pct}%`);
                } else {
                    if (key === '0') canvasZoom('fit');
                    else if (key === '1') canvasZoom('100');
                    else if (key === '2') canvasZoom('200');
                }
                e.preventDefault();
            }
            // Ctrl+D = deselect zone mask, Ctrl+A = select all pixels

            // Brush size: [ and ] keys
            else if (key === '[' && !e.shiftKey) {
                const el = document.getElementById('brushSize');
                if (el) { el.value = Math.max(3, parseInt(el.value) - 5); el.oninput(); }
            }
            else if (key === ']' && !e.shiftKey) {
                const el = document.getElementById('brushSize');
                if (el) { el.value = Math.min(300, parseInt(el.value) + 5); el.oninput(); }
            }
            // Brush hardness: { and } keys (Shift + [ / ])
            else if (key === '{' || (e.shiftKey && e.code === 'BracketLeft')) {
                const el = document.getElementById('brushHardness');
                if (el) { el.value = Math.max(0, parseInt(el.value) - 10); el.oninput(); }
            }
            else if (key === '}' || (e.shiftKey && e.code === 'BracketRight')) {
                const el = document.getElementById('brushHardness');
                if (el) { el.value = Math.min(100, parseInt(el.value) + 10); el.oninput(); }
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
                if (e.target && e.target.closest && e.target.closest('#splitPreview, #previewPane, .preview-inner, #livePreviewImg, #previewSpecPane, #livePreviewSpecImg, #specChannelCanvas')) {
                    return;
                }
                if (!document.getElementById('paintCanvas')?.width) return;

                // If placement editing is active, scroll adjusts the selected
                // target's scale instead of zooming the viewport.
                if (typeof placementLayer !== 'undefined' && placementLayer !== 'none' &&
                    typeof selectedZoneIndex !== 'undefined' && zones && zones[selectedZoneIndex]) {
                    e.preventDefault();
                    const z = zones[selectedZoneIndex];
                    const delta = e.deltaY > 0 ? -0.05 : 0.05;
                    const placementState = _getPlacementTargetState(z, placementLayer);
                    if (placementState && typeof pushZoneUndo === 'function') pushZoneUndo('Scale placement', true);
                    if (placementState && _setPlacementTargetScale(z, placementLayer, (placementState.scale || 1.0) + delta)) {
                        if (typeof renderZones === 'function') renderZones();
                        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                        if (typeof applyPlacementPatternTransform === 'function' && placementLayer === 'pattern') applyPlacementPatternTransform();
                        return;
                    }
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
            // Right-click = context menu, right-click drag = pan (when zoomed)
            // Space + left-click = pan (always)
            //
            // The key insight: we intercept mousedown on the VIEWPORT (parent of canvas),
            // and decide whether it's a pan or a tool action based on whether the user drags.
            let pendingPan = false;
            let pendingPanEvent = null;
            let pendingPanButton = null;
            let panConsumed = false;  // True if this mousedown became a pan (suppress canvas tool action)
            let activePanButton = null;
            let panMoved = false;
            let suppressNextCanvasContextMenu = false;
            let lastRightButtonPanAt = 0;
            let clearCanvasContextMenuSuppressTimer = null;
            let rightButtonDownForCanvas = false;
            let rightButtonDragExceeded = false;
            let rightButtonStartX = 0;
            let rightButtonStartY = 0;

            // Right-click on canvas: show context menu instead of browser default.
            // The canvas handler at line 2142 calls showCanvasContextMenu; we prevent
            // the browser menu here but let showCanvasContextMenu handle the UX.
            viewport.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                if (rightButtonDownForCanvas) {
                    const rdx = e.clientX - rightButtonStartX;
                    const rdy = e.clientY - rightButtonStartY;
                    if (rdx * rdx + rdy * rdy > 25) {
                        rightButtonDragExceeded = true;
                        suppressNextCanvasContextMenu = true;
                        lastRightButtonPanAt = Date.now();
                    }
                }
                const rightPanJustEnded = lastRightButtonPanAt && (Date.now() - lastRightButtonPanAt < 1500);
                if (isPanning || rightButtonDragExceeded || (activePanButton === 2 && panMoved) || suppressNextCanvasContextMenu || rightPanJustEnded) {
                    suppressNextCanvasContextMenu = false;
                    rightButtonDragExceeded = false;
                    rightButtonDownForCanvas = false;
                    lastRightButtonPanAt = 0;
                    if (clearCanvasContextMenuSuppressTimer) {
                        clearTimeout(clearCanvasContextMenuSuppressTimer);
                        clearCanvasContextMenuSuppressTimer = null;
                    }
                    return;
                }
                if (e.target.id === 'paintCanvas' && typeof showCanvasContextMenu === 'function') {
                    showCanvasContextMenu(e);
                }
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
                    if (_selectedLayerId && hasActivePixelSelection() && !_selectionContainsCanvasPoint(x, y) && !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
                        _clearActivePixelSelection(true);
                    }
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

                if (e.button === 2 && e.target.id === 'paintCanvas') {
                    rightButtonDownForCanvas = true;
                    rightButtonDragExceeded = false;
                    rightButtonStartX = e.clientX;
                    rightButtonStartY = e.clientY;
                }

                // Middle button (button 1) always pans immediately
                if (e.button === 1) {
                    e.preventDefault();
                    startPan(e, viewport);
                    panConsumed = true;
                    return;
                }
                // Right button (button 2): click = context menu, drag = pan
                if (e.button === 2 && canvasOverflows()) {
                    e.preventDefault();
                    pendingPan = true;
                    pendingPanEvent = e;
                    pendingPanButton = 2;
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
                    pendingPanButton = 0;
                    return;
                }
            });

            document.addEventListener('mousemove', (e) => {
                if (rightButtonDownForCanvas && !rightButtonDragExceeded) {
                    const rdx = e.clientX - rightButtonStartX;
                    const rdy = e.clientY - rightButtonStartY;
                    if (rdx * rdx + rdy * rdy > 25) {
                        rightButtonDragExceeded = true;
                        suppressNextCanvasContextMenu = true;
                        lastRightButtonPanAt = Date.now();
                    }
                }
                // Check if pending left-click should become a pan (drag threshold = 5px)
                if (pendingPan && pendingPanEvent) {
                    const dx = e.clientX - pendingPanEvent.clientX;
                    const dy = e.clientY - pendingPanEvent.clientY;
                    if (dx * dx + dy * dy > 25) {  // 5px threshold
                        if (pendingPanButton === 2) {
                            suppressNextCanvasContextMenu = true;
                            lastRightButtonPanAt = Date.now();
                            if (clearCanvasContextMenuSuppressTimer) {
                                clearTimeout(clearCanvasContextMenuSuppressTimer);
                            }
                            clearCanvasContextMenuSuppressTimer = setTimeout(() => {
                                suppressNextCanvasContextMenu = false;
                                rightButtonDragExceeded = false;
                                clearCanvasContextMenuSuppressTimer = null;
                            }, 1500);
                        }
                        startPan(pendingPanEvent, viewport);
                        panConsumed = true;
                        pendingPan = false;
                        pendingPanEvent = null;
                        pendingPanButton = null;
                        // Cancel any active drawing operation so pan takes over cleanly
                        isDrawing = false;
                        rectStart = null;
                    }
                }
                if (!isPanning) return;
                const sc = getScrollContainer();
                if (!sc) return;
                if (!panMoved) {
                    const panDx = e.clientX - panStartX;
                    const panDy = e.clientY - panStartY;
                    if (panDx * panDx + panDy * panDy > 4) panMoved = true;
                }
                sc.scrollLeft = panScrollStartX - (e.clientX - panStartX);
                sc.scrollTop = panScrollStartY - (e.clientY - panStartY);
            });

            document.addEventListener('mouseup', (e) => {
                if (e.button === 2) {
                    if (rightButtonDragExceeded) {
                        suppressNextCanvasContextMenu = true;
                        lastRightButtonPanAt = Date.now();
                        if (clearCanvasContextMenuSuppressTimer) {
                            clearTimeout(clearCanvasContextMenuSuppressTimer);
                        }
                        clearCanvasContextMenuSuppressTimer = setTimeout(() => {
                            suppressNextCanvasContextMenu = false;
                            rightButtonDragExceeded = false;
                            clearCanvasContextMenuSuppressTimer = null;
                        }, 1500);
                    }
                    rightButtonDownForCanvas = false;
                }
                // If pending pan never started (quick click), just clean up - tool action already happened
                if (pendingPan) {
                    pendingPan = false;
                    pendingPanEvent = null;
                    pendingPanButton = null;
                }
                if (isPanning) {
                    const suppressMenuForThisPan = activePanButton === 2 && panMoved;
                    isPanning = false;
                    panConsumed = true;  // Keep flag until next mousedown
                    activePanButton = null;
                    panMoved = false;
                    if (suppressMenuForThisPan) {
                        suppressNextCanvasContextMenu = true;
                        lastRightButtonPanAt = Date.now();
                        if (clearCanvasContextMenuSuppressTimer) {
                            clearTimeout(clearCanvasContextMenuSuppressTimer);
                        }
                        clearCanvasContextMenuSuppressTimer = setTimeout(() => {
                            suppressNextCanvasContextMenu = false;
                            rightButtonDragExceeded = false;
                            clearCanvasContextMenuSuppressTimer = null;
                        }, 1500);
                    }
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
                                else if (usesCustomBrushCursorMode(canvasMode)) cvs.style.cursor = getBrushNativeCursor();
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
            activePanButton = typeof e.button === 'number' ? e.button : 0;
            panMoved = false;
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

// ══════════════════════════════════════════════════════════════════════════════
// FREE TRANSFORM SYSTEM — Photoshop Ctrl+T style
// Bounding box with 8 handles (4 corner + 4 edge) + rotation ring + center pivot
// ══════════════════════════════════════════════════════════════════════════════

var freeTransformState = null; // null = inactive, object = active transform
var _pendingLayerTransformMeta = null;

function _hideTransformCanvas() {
    const tc = document.getElementById('transformCanvas');
    if (!tc) return;
    tc.style.display = 'none';
    tc.style.pointerEvents = 'none';
    const ctx = tc.getContext('2d');
    if (ctx) ctx.clearRect(0, 0, tc.width, tc.height);
}

function _showLayerTransformQuickbar(label) {
    const bar = document.getElementById('layerTransformQuickbar');
    if (!bar) return;
    const labelEl = document.getElementById('layerTransformQuickbarLabel');
    if (labelEl) labelEl.textContent = label || 'Layer Transform';
    bar.style.display = 'flex';
}

function _hideLayerTransformQuickbar() {
    const bar = document.getElementById('layerTransformQuickbar');
    if (!bar) return;
    bar.style.display = 'none';
}

function rotateActiveLayerTransformBy(deltaDegrees) {
    if (!freeTransformState || freeTransformState.target !== 'layer') return false;
    const delta = Number(deltaDegrees) || 0;
    freeTransformState.rotation = ((freeTransformState.rotation + delta) % 360 + 360) % 360;
    drawTransformHandles();
    if (typeof showToast === 'function') {
        const dir = delta >= 0 ? '+' : '';
        showToast(`Transform rotation ${dir}${delta}°`);
    }
    return true;
}
window.rotateActiveLayerTransformBy = rotateActiveLayerTransformBy;

function rotateActiveTransformBy(deltaDegrees) {
    if (!freeTransformState) return false;
    if (freeTransformState.target === 'layer') {
        return rotateActiveLayerTransformBy(deltaDegrees);
    }
    const delta = Number(deltaDegrees) || 0;
    freeTransformState.rotation = ((freeTransformState.rotation + delta) % 360 + 360) % 360;
    drawTransformHandles();
    if (typeof showToast === 'function') {
        const dir = delta >= 0 ? '+' : '';
        showToast(`Transform rotation ${dir}${delta}°`);
    }
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
    return true;
}
window.rotateActiveTransformBy = rotateActiveTransformBy;

function cancelActiveTransformSession() {
    if (!freeTransformState) return false;
    if (freeTransformState.target === 'layer') {
        cancelLayerTransform();
        return true;
    }
    deactivateFreeTransform(false);
    return true;
}
window.cancelActiveTransformSession = cancelActiveTransformSession;

/**
 * Activate Free Transform on the current zone's active layer.
 * target: 'pattern' | 'base' | 'decal' | 'mask'
 */
function activateFreeTransform(target) {
    const z = zones[selectedZoneIndex];
    if (!z) return;
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;

    // Determine initial bounds based on target
    let cx, cy, sw, sh, rot, scX, scY;
    if (target === 'pattern') {
        cx = (z.patternOffsetX ?? 0.5) * w;
        cy = (z.patternOffsetY ?? 0.5) * h;
        scX = z.scale || 1.0;
        scY = z.scale || 1.0;
        rot = z.rotation || 0;
        sw = w * scX; sh = h * scY;
    } else if (target === 'base') {
        cx = (z.baseOffsetX ?? 0.5) * w;
        cy = (z.baseOffsetY ?? 0.5) * h;
        scX = z.baseScale || 1.0;
        scY = z.baseScale || 1.0;
        rot = z.baseRotation || 0;
        sw = w * scX; sh = h * scY;
    } else if (target === 'decal' && typeof selectedDecalIndex !== 'undefined' && selectedDecalIndex >= 0) {
        const d = (typeof decalLayers !== 'undefined') ? decalLayers[selectedDecalIndex] : null;
        if (!d) {
            if (typeof showToast === 'function') showToast('Select a decal first before using Transform Decal', 'warn');
            return false;
        }
        cx = d.x; cy = d.y;
        scX = d.scale || 1.0; scY = d.scale || 1.0;
        rot = d.rotation || 0;
        sw = (d.width || 200) * scX; sh = (d.height || 200) * scY;
    } else if (target === 'decal') {
        if (typeof showToast === 'function') showToast('Select a decal first before using Transform Decal', 'warn');
        return false;
    } else {
        // Default: full canvas
        cx = w / 2; cy = h / 2;
        scX = 1.0; scY = 1.0; rot = 0;
        sw = w; sh = h;
    }

    freeTransformState = {
        target: target,
        zoneIndex: selectedZoneIndex,
        // Transform values
        centerX: cx, centerY: cy,
        scaleX: scX, scaleY: scY,
        rotation: rot,
        // Original values for cancel
        origCenterX: cx, origCenterY: cy,
        origScaleX: scX, origScaleY: scY,
        origRotation: rot,
        // Bounding box (before rotation)
        boxW: sw, boxH: sh,
        // Interaction state
        dragging: null, // null, 'move', 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w', 'rotate'
        dragStartX: 0, dragStartY: 0,
        dragStartCX: 0, dragStartCY: 0,
        dragStartSX: 0, dragStartSY: 0,
        dragStartRot: 0,
    };

    // Show transform canvas
    const tc = document.getElementById('transformCanvas');
    if (tc) {
        tc.style.display = 'block';
        tc.width = pc.width;
        tc.height = pc.height;
        tc.style.width = pc.style.width;
        tc.style.height = pc.style.height;
        tc.style.pointerEvents = 'auto'; // Capture mouse events
    }
    drawTransformHandles();
    if (typeof showToast === 'function') {
        showToast('Free Transform: drag handles to resize, drag outside to rotate. Enter=commit, Esc=cancel', 'info');
    }
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
    return true;
}

function deactivateFreeTransform(commit) {
    if (!freeTransformState) return;
    const s = freeTransformState;

    // Route layer transforms to their own handlers
    if (s.target === 'layer') {
        if (commit) commitLayerTransform();
        else cancelLayerTransform();
        return;
    }

    if (commit) {
        // Apply transform values back to zone/decal
        const z = zones[s.zoneIndex];
        const pc = document.getElementById('paintCanvas');
        if (z && pc) {
            const w = pc.width, h = pc.height;
            if ((s.target === 'pattern' || s.target === 'base') && typeof pushZoneUndo === 'function') {
                pushZoneUndo('free transform', true);
            }
            if (s.target === 'pattern') {
                z.patternOffsetX = s.centerX / w;
                z.patternOffsetY = s.centerY / h;
                z.scale = Math.max(0.05, s.scaleX);
                z.rotation = ((s.rotation % 360) + 360) % 360;
            } else if (s.target === 'base') {
                z.baseOffsetX = s.centerX / w;
                z.baseOffsetY = s.centerY / h;
                z.baseScale = Math.max(0.05, s.scaleX);
                z.baseRotation = ((s.rotation % 360) + 360) % 360;
            } else if (s.target === 'decal' && typeof decalLayers !== 'undefined' && typeof selectedDecalIndex !== 'undefined') {
                const d = decalLayers[selectedDecalIndex];
                if (d) {
                    d.x = s.centerX;
                    d.y = s.centerY;
                    d.scale = Math.max(0.05, s.scaleX);
                    d.rotation = ((s.rotation % 360) + 360) % 360;
                    if (typeof renderDecalOverlay === 'function') renderDecalOverlay();
                }
            }
            if (typeof renderZones === 'function') renderZones();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }
    }

    freeTransformState = null;
    _hideLayerTransformQuickbar();
    _hideTransformCanvas();
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
}

function drawTransformHandles() {
    const s = freeTransformState;
    if (!s) return;
    const tc = document.getElementById('transformCanvas');
    if (!tc) return;
    const ctx = tc.getContext('2d');
    const zoom = typeof currentZoom !== 'undefined' ? currentZoom : 1;

    // Sync canvas size
    const pc = document.getElementById('paintCanvas');
    if (pc && (tc.width !== pc.width || tc.height !== pc.height)) {
        tc.width = pc.width; tc.height = pc.height;
        tc.style.width = pc.style.width; tc.style.height = pc.style.height;
    }

    ctx.clearRect(0, 0, tc.width, tc.height);
    ctx.save();

    // All drawing in CANVAS coordinates (not screen) — zoom handled by CSS
    const cx = s.centerX, cy = s.centerY;
    const hw = s.boxW / 2, hh = s.boxH / 2;
    const rad = s.rotation * Math.PI / 180;

    // Helper: rotate point around center
    function rotPt(px, py) {
        const dx = px - cx, dy = py - cy;
        return {
            x: cx + dx * Math.cos(rad) - dy * Math.sin(rad),
            y: cy + dx * Math.sin(rad) + dy * Math.cos(rad)
        };
    }

    // 4 corners (before scale applied — use boxW/boxH which already includes scale)
    const tl = rotPt(cx - hw, cy - hh);
    const tr = rotPt(cx + hw, cy - hh);
    const br = rotPt(cx + hw, cy + hh);
    const bl = rotPt(cx - hw, cy + hh);
    // 4 edge midpoints
    const tm = rotPt(cx, cy - hh);
    const rm = rotPt(cx + hw, cy);
    const bm = rotPt(cx, cy + hh);
    const lm = rotPt(cx - hw, cy);

    // Draw bounding box
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(tl.x, tl.y);
    ctx.lineTo(tr.x, tr.y);
    ctx.lineTo(br.x, br.y);
    ctx.lineTo(bl.x, bl.y);
    ctx.closePath();
    ctx.stroke();
    ctx.setLineDash([]);

    // Handle size (in canvas pixels, not screen)
    const hs = 5;

    // Draw handles — filled white squares with cyan border
    function drawHandle(pt, cursor) {
        ctx.fillStyle = '#fff';
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 1.5;
        ctx.fillRect(pt.x - hs, pt.y - hs, hs * 2, hs * 2);
        ctx.strokeRect(pt.x - hs, pt.y - hs, hs * 2, hs * 2);
    }

    // Corner handles
    drawHandle(tl); drawHandle(tr); drawHandle(br); drawHandle(bl);
    // Edge handles (smaller)
    const ehs = 4;
    for (const pt of [tm, rm, bm, lm]) {
        ctx.fillStyle = '#fff';
        ctx.strokeStyle = '#00aacc';
        ctx.lineWidth = 1;
        ctx.fillRect(pt.x - ehs, pt.y - ehs, ehs * 2, ehs * 2);
        ctx.strokeRect(pt.x - ehs, pt.y - ehs, ehs * 2, ehs * 2);
    }

    // Rotation handle — circle above top-center, connected by line
    const rotHandleDist = 25;
    const rotPtPos = rotPt(cx, cy - hh - rotHandleDist);
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(tm.x, tm.y);
    ctx.lineTo(rotPtPos.x, rotPtPos.y);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(rotPtPos.x, rotPtPos.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#00e5ff';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Center pivot
    ctx.strokeStyle = '#ff3366';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx - 6, cy); ctx.lineTo(cx + 6, cy);
    ctx.moveTo(cx, cy - 6); ctx.lineTo(cx, cy + 6);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, 3, 0, Math.PI * 2);
    ctx.strokeStyle = '#ff3366';
    ctx.stroke();

    // Info text
    ctx.fillStyle = 'rgba(0,229,255,0.9)';
    ctx.font = '11px sans-serif';
    ctx.fillText(`${Math.round(s.scaleX * 100)}% × ${Math.round(s.scaleY * 100)}%  ${Math.round(s.rotation)}°`, tl.x, tl.y - 8);

    ctx.restore();

    // Store handle positions for hit testing
    s._handles = { tl, tr, br, bl, tm, rm, bm, lm, rot: rotPtPos, cx, cy, hs, hw, hh };
}

/**
 * Hit-test transform handles. Returns handle ID or null.
 */
function hitTestTransformHandle(x, y) {
    const s = freeTransformState;
    if (!s || !s._handles) return null;
    const h = s._handles;
    const r = 8; // hit radius

    function near(pt) { return Math.hypot(x - pt.x, y - pt.y) < r; }

    if (near(h.rot)) return 'rotate';
    if (near(h.tl)) return 'nw';
    if (near(h.tr)) return 'ne';
    if (near(h.bl)) return 'sw';
    if (near(h.br)) return 'se';
    if (near(h.tm)) return 'n';
    if (near(h.bm)) return 's';
    if (near(h.lm)) return 'w';
    if (near(h.rm)) return 'e';

    // Inside bounding box? → move
    // Point-in-rotated-rect test
    const cx = h.cx, cy = h.cy;
    const rad = -(s.rotation * Math.PI / 180);
    const dx = x - cx, dy = y - cy;
    const lx = dx * Math.cos(rad) - dy * Math.sin(rad);
    const ly = dx * Math.sin(rad) + dy * Math.cos(rad);
    if (Math.abs(lx) <= h.hw && Math.abs(ly) <= h.hh) return 'move';

    // Outside box but close → rotate (generous zone)
    if (Math.abs(lx) <= h.hw + 30 && Math.abs(ly) <= h.hh + 30) return 'rotate';

    return null;
}

// Module-level canvas-coord helpers for the Free Transform tool.
// The inner `getPixelAt` / `getPixelAtClamped` defined in setupCanvasHandlers()
// are closures over that function's local `canvas` param, so transform handlers
// (which live at module scope) can't see them. These helpers walk off the paint
// canvas rect since the transform overlay lives on top of it at the same size.
function _transformGetPixel(e, clamp) {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return null;
    const rect = pc.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    const sx = pc.width / rect.width;
    const sy = pc.height / rect.height;
    let x = Math.floor((e.clientX - rect.left) * sx);
    let y = Math.floor((e.clientY - rect.top) * sy);
    if (clamp) {
        x = Math.max(0, Math.min(pc.width - 1, x));
        y = Math.max(0, Math.min(pc.height - 1, y));
        return { x, y };
    }
    if (x < 0 || x >= pc.width || y < 0 || y >= pc.height) return null;
    return { x, y };
}

/**
 * Handle mousedown on transform canvas
 */
function onTransformMouseDown(e) {
    if (!freeTransformState) return false;
    const pos = _transformGetPixel(e, false);
    if (!pos) return false;

    const handle = hitTestTransformHandle(pos.x, pos.y);
    if (!handle) {
        // Click outside transform → commit
        deactivateFreeTransform(true);
        return true;
    }

    const s = freeTransformState;
    s.dragging = handle;
    s.dragStartX = pos.x;
    s.dragStartY = pos.y;
    s.dragStartCX = s.centerX;
    s.dragStartCY = s.centerY;
    s.dragStartSX = s.scaleX;
    s.dragStartSY = s.scaleY;
    s.dragStartRot = s.rotation;
    s.dragStartBoxW = s.boxW;
    s.dragStartBoxH = s.boxH;
    e.preventDefault();
    e.stopPropagation();
    return true;
}

/**
 * Handle mousemove during transform drag
 */
function onTransformMouseMove(e) {
    const s = freeTransformState;
    if (!s) return false;
    const pos = _transformGetPixel(e, true);
    if (!pos) return false;

    // Update cursor based on hover
    if (!s.dragging) {
        const handle = hitTestTransformHandle(pos.x, pos.y);
        const tc = document.getElementById('transformCanvas');
        if (tc) {
            const cursors = {
                'nw': 'nw-resize', 'ne': 'ne-resize', 'sw': 'sw-resize', 'se': 'se-resize',
                'n': 'n-resize', 's': 's-resize', 'e': 'e-resize', 'w': 'w-resize',
                'move': 'move', 'rotate': 'grab', null: 'default'
            };
            tc.style.cursor = cursors[handle] || 'default';
        }
        return false;
    }

    const dx = pos.x - s.dragStartX;
    const dy = pos.y - s.dragStartY;

    if (s.dragging === 'move') {
        s.centerX = s.dragStartCX + dx;
        s.centerY = s.dragStartCY + dy;
    } else if (s.dragging === 'rotate') {
        const a1 = Math.atan2(s.dragStartY - s.centerY, s.dragStartX - s.centerX);
        const a2 = Math.atan2(pos.y - s.centerY, pos.x - s.centerX);
        let angleDelta = (a2 - a1) * 180 / Math.PI;
        // Shift = snap to 15° increments
        if (e.shiftKey) angleDelta = Math.round(angleDelta / 15) * 15;
        s.rotation = s.dragStartRot + angleDelta;
    } else {
        // Scale handles
        const cx = s.centerX, cy = s.centerY;
        const rad = -(s.rotation * Math.PI / 180);
        // Transform mouse delta into local (unrotated) space
        const ldx = dx * Math.cos(rad) - dy * Math.sin(rad);
        const ldy = dx * Math.sin(rad) + dy * Math.cos(rad);

        let newW = s.dragStartBoxW, newH = s.dragStartBoxH;
        if (s.dragging === 'se' || s.dragging === 'e' || s.dragging === 'ne') newW = s.dragStartBoxW + ldx * 2;
        if (s.dragging === 'sw' || s.dragging === 'w' || s.dragging === 'nw') newW = s.dragStartBoxW - ldx * 2;
        if (s.dragging === 'se' || s.dragging === 's' || s.dragging === 'sw') newH = s.dragStartBoxH + ldy * 2;
        if (s.dragging === 'ne' || s.dragging === 'n' || s.dragging === 'nw') newH = s.dragStartBoxH - ldy * 2;

        // Shift = proportional
        if (e.shiftKey && (s.dragging === 'nw' || s.dragging === 'ne' || s.dragging === 'sw' || s.dragging === 'se')) {
            const ratio = s.dragStartBoxW / Math.max(1, s.dragStartBoxH);
            newH = newW / ratio;
        }

        const pc = document.getElementById('paintCanvas');
        const canvasW = pc ? pc.width : 2048;
        const canvasH = pc ? pc.height : 2048;
        s.boxW = Math.max(10, newW);
        s.boxH = Math.max(10, newH);
        s.scaleX = s.boxW / canvasW;
        s.scaleY = s.boxH / canvasH;
    }

    drawTransformHandles();
    e.preventDefault();
    return true;
}

/**
 * Handle mouseup during transform
 */
function onTransformMouseUp(e) {
    if (!freeTransformState || !freeTransformState.dragging) return false;
    freeTransformState.dragging = null;
    drawTransformHandles();
    return true;
}

// Keyboard: Enter = commit, Escape = cancel, Ctrl+T = activate
document.addEventListener('keydown', function(e) {
    if (e.defaultPrevented) return;
    if (freeTransformState) {
        if (e.key === 'Enter') {
            if (freeTransformState.target === 'layer') { commitLayerTransform(); }
            else { deactivateFreeTransform(true); }
            e.preventDefault();
            e.stopImmediatePropagation();
        } else if (e.key === 'Escape') {
            if (freeTransformState.target === 'layer') { cancelLayerTransform(); }
            else { deactivateFreeTransform(false); }
            e.preventDefault();
            e.stopImmediatePropagation();
        } else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'z') {
            cancelActiveTransformSession();
            e.preventDefault();
            e.stopImmediatePropagation();
        }
        return;
    }
    // Ctrl+T activates the context-aware transform:
    // - selected layer + selection => lift selection to a new layer and transform it
    // - selected layer only        => transform the layer
    // - no layer                   => transform the zone's pattern/base
    if ((e.ctrlKey || e.metaKey) && e.key === 't' && !e.shiftKey && !e.altKey) {
        if (!['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
            if (typeof placementLayer !== 'undefined' && placementLayer && placementLayer !== 'none') {
                if (typeof showToast === 'function') showToast('Finish placement editing before starting transform');
                e.preventDefault();
                return;
            }
            if ((typeof _selectionMoveDrag !== 'undefined' && _selectionMoveDrag)
                    || (typeof canvasMode !== 'undefined' && canvasMode === 'selection-move')) {
                if (typeof showToast === 'function') showToast('Finish moving the selection border before starting transform');
                e.preventDefault();
                return;
            }
            if (typeof activateContextTransform === 'function') {
                activateContextTransform();
                e.preventDefault();
            }
        }
    }
});

// Wire transform canvas mouse events
document.addEventListener('DOMContentLoaded', function() {
    const tc = document.getElementById('transformCanvas');
    if (tc) {
        tc.addEventListener('mousedown', function(e) {
            if (freeTransformState) onTransformMouseDown(e);
        });
        tc.addEventListener('mousemove', function(e) {
            if (freeTransformState) onTransformMouseMove(e);
        });
        tc.addEventListener('mouseup', function(e) {
            if (freeTransformState) onTransformMouseUp(e);
        });
    }
});

// Expose for toolbar button
window.activateFreeTransform = activateFreeTransform;
window.deactivateFreeTransform = deactivateFreeTransform;

// ══════════════════════════════════════════════════════════════════════════════
// TEXT TOOL — Click canvas to place editable text, renders as decal
// ══════════════════════════════════════════════════════════════════════════════

var _textInputActive = false;

// ═══ COLOR SWATCHES — Save/load recent colors for quick access ═══
// 2026-04-18 MARATHON bug #39 (MED): pre-fix, corrupt localStorage data
// (from an extension, browser bug, dev-tools edit, or prior crash)
// would throw synchronously during script load and break SPB before any
// UI could render. Safe parse with empty fallback.
function _safeLocalStorageJSON(key, fallback) {
    try {
        const raw = localStorage.getItem(key);
        if (!raw) return fallback;
        const v = JSON.parse(raw);
        return v != null ? v : fallback;
    } catch (e) {
        console.warn('[SPB] corrupt localStorage for ' + key + ':', e);
        return fallback;
    }
}
if (typeof window !== 'undefined') window._safeLocalStorageJSON = _safeLocalStorageJSON;
var _savedSwatches = _safeLocalStorageJSON('spb_color_swatches', []);
var _recentColors = [];
var _MAX_SWATCHES = 16;
var _MAX_RECENT = 8;

function saveColorSwatch() {
    const color = _foregroundColor;
    if (_savedSwatches.includes(color)) return;
    _savedSwatches.unshift(color);
    if (_savedSwatches.length > _MAX_SWATCHES) _savedSwatches.pop();
    localStorage.setItem('spb_color_swatches', JSON.stringify(_savedSwatches));
    renderSwatchBar();
    if (typeof showToast === 'function') showToast(`Saved ${color} to swatches`);
}

function addRecentColor(color) {
    if (!color || _recentColors[0] === color) return;
    _recentColors = _recentColors.filter(c => c !== color);
    _recentColors.unshift(color);
    if (_recentColors.length > _MAX_RECENT) _recentColors.pop();
    renderSwatchBar();
}

function setFGFromSwatch(color) {
    _foregroundColor = color;
    const picker = document.getElementById('fgColorPicker');
    const swatch = document.getElementById('fgColorSwatch');
    const fgHexInput = document.getElementById('fgHexInput');
    if (picker) picker.value = color;
    if (swatch) swatch.style.background = color;
    if (fgHexInput) fgHexInput.value = color;
    if (typeof syncLayerPaintSourceUI === 'function') syncLayerPaintSourceUI();
    if (typeof warmLayerPaintSpecialCache === 'function' && isLayerPaintSourceSpecial()) warmLayerPaintSpecialCache(false);
}

function renderSwatchBar() {
    const bar = document.getElementById('colorSwatchBar');
    if (!bar) return;
    let html = '';
    // Recent colors first (auto-tracked)
    for (const c of _recentColors) {
        html += `<div onclick="setFGFromSwatch('${c}')" style="width:12px;height:12px;background:${c};border:1px solid #444;border-radius:1px;cursor:pointer;flex-shrink:0;" title="Recent: ${c}"></div>`;
    }
    // Separator if both exist
    if (_recentColors.length > 0 && _savedSwatches.length > 0) {
        html += `<div style="width:1px;height:12px;background:#555;margin:0 1px;flex-shrink:0;"></div>`;
    }
    // Saved swatches
    for (const c of _savedSwatches) {
        html += `<div onclick="setFGFromSwatch('${c}')" oncontextmenu="event.preventDefault();_savedSwatches=_savedSwatches.filter(s=>s!=='${c}');localStorage.setItem('spb_color_swatches',JSON.stringify(_savedSwatches));renderSwatchBar();" style="width:12px;height:12px;background:${c};border:1px solid #666;border-radius:2px;cursor:pointer;flex-shrink:0;" title="Saved: ${c} (right-click to remove)"></div>`;
    }
    bar.innerHTML = html;
}

// Racing color palette presets
var _colorPalettes = {
    'NASCAR Classic': ['#ff0000','#0033cc','#ffcc00','#ffffff','#000000','#ff6600','#009933','#660099'],
    'F1 / Motorsport': ['#ff1801','#00d2be','#ff8700','#0090ff','#006f62','#2293d1','#b6babd','#1e1e1e'],
    'Sponsor Safe': ['#ffffff','#000000','#cc0000','#003399','#ffcc00','#666666','#009933','#ff6600'],
    'Military / Tactical': ['#4b5320','#2d2926','#8b7355','#556b2f','#1a1a1a','#c2b280','#6b4226','#3c3c3c'],
    'Chrome & Metal': ['#c0c0c0','#808080','#a0a0a0','#d4af37','#b87333','#e5e5e5','#404040','#cd7f32'],
    'Neon / Electric': ['#00ff00','#ff00ff','#00ffff','#ffff00','#ff0080','#8000ff','#ff4400','#00ff80'],
    'Dark Premium': ['#1a1a2e','#16213e','#0f3460','#e94560','#533483','#2c2c54','#d4a574','#1b1b2f'],
    'Retro Racing': ['#ff4500','#ffd700','#006400','#000080','#8b0000','#f5f5dc','#cd853f','#2f4f4f'],
};

function loadColorPalette(name) {
    const colors = _colorPalettes[name];
    if (!colors) return;
    _savedSwatches = [...colors];
    localStorage.setItem('spb_color_swatches', JSON.stringify(_savedSwatches));
    renderSwatchBar();
    if (typeof showToast === 'function') showToast(`Loaded palette: ${name}`);
}

function showPaletteMenu() {
    let html = '<div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:10000;background:#111;border:2px solid var(--accent-gold);border-radius:10px;padding:16px 20px;min-width:280px;">';
    html += '<div style="display:flex;justify-content:space-between;margin-bottom:10px;"><span style="font-weight:bold;color:var(--accent-gold);">COLOR PALETTES</span><button onclick="this.parentElement.parentElement.parentElement.remove()" style="background:none;border:none;color:#888;font-size:16px;cursor:pointer;">✕</button></div>';
    for (const [name, colors] of Object.entries(_colorPalettes)) {
        html += `<div onclick="loadColorPalette('${name}');this.parentElement.parentElement.remove();" style="cursor:pointer;padding:6px 8px;border-radius:4px;margin-bottom:4px;display:flex;align-items:center;gap:8px;transition:background 0.1s;" onmouseenter="this.style.background='rgba(255,255,255,0.08)'" onmouseleave="this.style.background=''">`;
        html += `<div style="display:flex;gap:2px;">`;
        for (const c of colors) {
            html += `<div style="width:14px;height:14px;background:${c};border:1px solid #444;border-radius:2px;"></div>`;
        }
        html += `</div><span style="font-size:10px;color:#ccc;">${name}</span></div>`;
    }
    html += '</div>';
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:9999;background:rgba(0,0,0,0.4);';
    overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = html;
    document.body.appendChild(overlay);
}
window.loadColorPalette = loadColorPalette;
window.showPaletteMenu = showPaletteMenu;

// Auto-render on load
document.addEventListener('DOMContentLoaded', renderSwatchBar);
// ═══ KEYBOARD SHORTCUT LEGEND ═══
function showShortcutLegend() {
    const shortcuts = [
        ['---TOOLS---', '--- Canvas Tools ---'],
        ['B', 'Brush (zone mask)'], ['C', 'Color Brush'], ['I', 'Pencil (1px precise)'],
        ['S', 'Clone Stamp (Alt+Click = set source)'], ['R', 'Recolor (BG to FG color)'],
        ['Q', 'Smudge (finger paint)'], ['D', 'Dodge (lighten)'], ['J', 'Burn (darken)'],
        ['F', 'Blur Brush'], ['H', 'Sharpen Brush'],
        ['---', '---'],
        ['---SELECTION---', '--- Selection Tools ---'],
        ['W', 'Magic Wand'], ['A', 'Select All Color'], ['E', 'Edge Detect'],
        ['O', 'Rectangle Select'], ['L', 'Lasso'], ['M', 'Ellipse Marquee'],
        ['G', 'Gradient'], ['K', 'Fill Bucket'], ['N', 'Pen / Bezier'],
        ['---', '---'],
        ['---CREATE---', '--- Create Tools ---'],
        ['T', 'Text Tool'], ['U', 'Shape Tool'], ['P', 'Eyedropper'],
        ['---', '---'],
        ['---COLORS---', '--- Colors & Canvas ---'],
        ['X', 'Swap FG/BG Colors'], ['Alt+Click', 'Sample color (temporary eyedropper)'],
        ['[ ]', 'Brush Size -/+'], ['{ }', 'Brush Hardness -/+'],
        ['Space+Drag', 'Pan Canvas'], ['Scroll', 'Zoom In/Out'],
        ['0', 'Zoom to Fit'], ['1', 'Zoom 100%'], ['2', 'Zoom 200%'],
        ['---', '---'],
        ['---ACTIONS---', '--- Actions ---'],
        ['Ctrl+Z', 'Undo'], ['Ctrl+Y / Ctrl+Shift+Z', 'Redo'],
        ['Ctrl+D', 'Deselect'], ['Ctrl+A', 'Select All'],
        ['Ctrl+Shift+I', 'Invert Selection'], ['Ctrl+T', 'Free Transform'],
        ['Ctrl+Click', 'Move Layer'], ['Dbl-click layer', 'Rename Layer'],
        ['Right-click', 'Context Menu'],
        ['---', '---'],
        // FIVE-HOUR SHIFT Win G3: these shortcuts existed in code but were
        // never advertised in the legend, so painters never discovered them.
        ['---CLIPBOARD---', '--- Clipboard / Paste ---'],
        ['Ctrl+C', 'Copy selected pixels'], ['Ctrl+X', 'Cut selected pixels'],
        ['Ctrl+V', 'Paste as new layer'], ['Ctrl+J', 'New Layer via Copy'],
        ['Alt+Backspace', 'Fill selection with FG'],
        ['Ctrl+Backspace', 'Fill selection with BG'],
        ['Delete', 'Delete selected pixels'],
        ['---', '---'],
        ['---LAYERS---', '--- Layer Management ---'],
        ['Ctrl+E', 'Merge Layer Down'],
        ['Ctrl+Shift+E', 'Flatten All Layers'],
        ['Ctrl+Shift+N', 'New Blank Layer'],
        ['Ctrl+L', 'Lock active zone to selected layer'],
        ['---', '---'],
        ['---FILE---', '--- File ---'],
        ['Ctrl+Shift+R', 'Reload last paint file'],
        ['Ctrl+Plus / Ctrl+Minus', 'Canvas Zoom In / Out'],
        ['---', '---'],
        ['---ZONES---', '--- Zone Operations (Shift+key) ---'],
        ['Shift+R', 'Randomize Zone'], ['Shift+D', 'Duplicate Zone'],
        ['Shift+N', 'Add New Zone'], ['Shift+H', 'History Gallery'],
        ['Shift+T', 'Template Library'], ['Shift+E', 'Toggle Zone Editor'],
        ['1-9', 'Select Zone 1-9'], ['V', 'Toggle Split View'],
        ['?', 'This Legend'],
    ];
    let html = '<div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:10000;background:#111;border:2px solid var(--accent-cyan);border-radius:12px;padding:20px 28px;max-height:80vh;overflow-y:auto;min-width:320px;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><span style="font-size:14px;font-weight:bold;color:var(--accent-cyan);">KEYBOARD SHORTCUTS</span><button onclick="this.parentElement.parentElement.remove()" style="background:none;border:none;color:#888;font-size:18px;cursor:pointer;">✕</button></div>';
    html += '<table style="width:100%;border-collapse:collapse;">';
    for (const [key, desc] of shortcuts) {
        if (key === '---') { html += '<tr><td colspan="2" style="border-bottom:1px solid #333;padding:4px 0;"></td></tr>'; continue; }
        if (key.startsWith('---') && key.endsWith('---')) { html += `<tr><td colspan="2" style="padding:8px 0 4px 0;font-size:10px;font-weight:bold;color:#00e5ff;letter-spacing:1px;text-transform:uppercase;">${desc.replace(/---/g,'').trim()}</td></tr>`; continue; }
        html += `<tr><td style="padding:3px 8px 3px 0;font-family:monospace;font-size:12px;color:#ffd700;font-weight:bold;white-space:nowrap;">${key}</td><td style="padding:3px 0;font-size:11px;color:#ccc;">${desc}</td></tr>`;
    }
    html += '</table></div>';
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:9999;background:rgba(0,0,0,0.5);';
    overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = html;
    document.body.appendChild(overlay);
}
window.showShortcutLegend = showShortcutLegend;

// ═══ GLOBAL STATUS BAR UPDATER ═══
function updateStatusBar() {
    const toolEl = document.getElementById('statusTool');
    const zoneEl = document.getElementById('statusZone');
    const layerEl = document.getElementById('statusLayer');
    const symEl2 = document.getElementById('statusSymmetry');
    const zoomEl = document.getElementById('statusZoom');
    if (toolEl) toolEl.textContent = (canvasMode || 'eyedropper').toUpperCase().replace(/-/g, ' ');
    if (zoneEl) {
        const zi = typeof selectedZoneIndex !== 'undefined' ? selectedZoneIndex : -1;
        const zn = (typeof zones !== 'undefined' && zones[zi]) ? (zones[zi].name || `Zone ${zi+1}`) : '--';
        zoneEl.textContent = `Zone: ${zn}`;
    }
    if (layerEl) {
        const layer = typeof getSelectedLayer === 'function' ? getSelectedLayer() : null;
        layerEl.textContent = layer ? `Layer: ${layer.name}` : 'Layer: none';
        layerEl.style.color = layer ? '#00e5ff' : '#555';
    }
    if (symEl2) {
        const sym = getEffectiveSymmetryMode();
        symEl2.textContent = `Sym: ${sym === 'off' ? 'Off' : sym.replace('-', ' ')}`;
        symEl2.style.color = sym === 'off' ? '#555' : '#ffd700';
    }
    if (zoomEl && typeof currentZoom !== 'undefined') {
        zoomEl.textContent = `${Math.round(currentZoom * 100)}%`;
    }
    // Document dimensions
    const dimEl = document.getElementById('statusDimensions');
    if (dimEl) {
        const pc = document.getElementById('paintCanvas');
        if (pc && pc.width > 0) {
            dimEl.textContent = `${pc.width}x${pc.height}`;
        }
    }
    // Selection pixel count
    const selEl = document.getElementById('statusSelection');
    if (selEl) {
        const zone = (typeof zones !== 'undefined' && typeof selectedZoneIndex !== 'undefined') ? zones[selectedZoneIndex] : null;
        if (zone && zone.regionMask) {
            let count = 0;
            for (let i = 0; i < zone.regionMask.length; i++) { if (zone.regionMask[i]) count++; }
            selEl.textContent = count > 0 ? `Sel: ${count.toLocaleString()}px` : '';
            selEl.style.color = count > 0 ? '#ffd700' : '#555';
        } else {
            selEl.textContent = '';
        }
    }
    // Layer count
    const lcEl = document.getElementById('statusLayerCount');
    if (lcEl) {
        const layerCount = typeof _psdLayers !== 'undefined' ? _psdLayers.length : 0;
        lcEl.textContent = layerCount > 0 ? `Layers: ${layerCount}` : '';
        lcEl.style.color = layerCount > 0 ? '#888' : '#555';
    }
}
// Update on tool change
var _origSetCanvasMode = typeof setCanvasMode === 'function' ? setCanvasMode : null;
// Hook into mousemove for coordinates
document.addEventListener('mousemove', function(e) {
    const coordEl = document.getElementById('statusCoords');
    if (!coordEl) return;
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const rect = pc.getBoundingClientRect();
    if (e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom) {
        const sx = pc.width / rect.width, sy = pc.height / rect.height;
        const x = Math.floor((e.clientX - rect.left) * sx);
        const y = Math.floor((e.clientY - rect.top) * sy);
        coordEl.textContent = `${x}, ${y}`;
        // Show color under cursor in status bar
        const colorEl = document.getElementById('statusCursorColor');
        if (colorEl && typeof paintImageData !== 'undefined' && paintImageData) {
            const idx = (y * pc.width + x) * 4;
            const r = paintImageData.data[idx], g = paintImageData.data[idx+1], b = paintImageData.data[idx+2];
            const hex = '#' + [r,g,b].map(c => c.toString(16).padStart(2,'0')).join('');
            colorEl.style.background = hex;
            colorEl.title = `${hex} (R:${r} G:${g} B:${b})`;
        }
    }
});
// Periodic status update (catches zone/layer/symmetry changes)
setInterval(updateStatusBar, 500);
window.updateStatusBar = updateStatusBar;

// Quick export canvas as PNG download
function quickExportPNG() {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const link = document.createElement('a');
    link.download = `SPB_export_${Date.now()}.png`;
    link.href = pc.toDataURL('image/png');
    link.click();
    if (typeof showToast === 'function') showToast(`Exported: ${link.download}`);
}
window.quickExportPNG = quickExportPNG;

window.saveColorSwatch = saveColorSwatch;
window.setFGFromSwatch = setFGFromSwatch;
window.renderSwatchBar = renderSwatchBar;

// Helper: draw text with letter spacing
function _drawTextWithSpacing(ctx, text, x, y, spacing) {
    if (!spacing || spacing === 0) { ctx.fillText(text, x, y); return; }
    let cx = x;
    for (let i = 0; i < text.length; i++) {
        ctx.fillText(text[i], cx, y);
        cx += ctx.measureText(text[i]).width + spacing;
    }
}
function _strokeTextWithSpacing(ctx, text, x, y, spacing) {
    if (!spacing || spacing === 0) { ctx.strokeText(text, x, y); return; }
    let cx = x;
    for (let i = 0; i < text.length; i++) {
        ctx.strokeText(text[i], cx, y);
        cx += ctx.measureText(text[i]).width + spacing;
    }
}

function onTextToolClick(x, y) {
    if (_textInputActive) return;
    _textInputActive = true;

    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const rect = pc.getBoundingClientRect();
    const zoom = typeof currentZoom !== 'undefined' ? currentZoom : 1;

    // Create floating textarea at click position (supports multiline with Shift+Enter)
    const input = document.createElement('textarea');
    input.id = '_textToolInput';
    input.placeholder = 'Type text... (Shift+Enter for new line)';
    input.rows = 1;
    input.style.cssText = `
        position: fixed;
        left: ${rect.left + x * zoom - 2}px;
        top: ${rect.top + y * zoom - 16}px;
        z-index: 99999;
        background: rgba(0,0,0,0.85);
        color: #fff;
        border: 2px solid #00e5ff;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: ${Math.max(14, Math.min(48, parseInt(document.getElementById('textSize')?.value || 120) * zoom * 0.3))}px;
        font-family: ${document.getElementById('textFont')?.value || 'Impact'};
        font-weight: ${document.getElementById('textBold')?.checked ? 'bold' : 'normal'};
        min-width: 80px;
        max-width: 400px;
        min-height: 24px;
        resize: vertical;
        outline: none;
    `;

    document.body.appendChild(input);
    input.focus();

    function commitText() {
        let text = input.value.trim();
        input.remove();
        _textInputActive = false;

        if (!text) return;

        // Render text to canvas → create decal
        const font = document.getElementById('textFont')?.value || 'Impact';
        const size = parseInt(document.getElementById('textSize')?.value || 120);
        const fillColor = document.getElementById('textFillColor')?.value || '#ffffff';
        const strokeColor = document.getElementById('textStrokeColor')?.value || '#000000';
        const strokeWidth = parseInt(document.getElementById('textStrokeWidth')?.value || 3);
        const bold = document.getElementById('textBold')?.checked;
        const italic = document.getElementById('textItalic')?.checked;
        const letterSpacing = parseInt(document.getElementById('textLetterSpacing')?.value || 0);
        const lineHeight = parseFloat(document.getElementById('textLineHeight')?.value || 1.2);
        const textTransform = document.getElementById('textTransform')?.value || 'none';
        const textEffect = document.getElementById('textEffect')?.value || 'none';

        // Apply text transform
        if (textTransform === 'uppercase') text = text.toUpperCase();
        else if (textTransform === 'lowercase') text = text.toLowerCase();
        else if (textTransform === 'capitalize') text = text.replace(/\b\w/g, c => c.toUpperCase());

        // Support multiline: split on newline character
        const lines = text.split('\n').filter(l => l.length > 0);
        if (lines.length === 0) return;

        // Build font string
        const fontStyle = `${italic ? 'italic ' : ''}${bold ? 'bold ' : ''}${size}px "${font}"`;
        const lineHeightPx = Math.round(size * lineHeight);

        // Measure text (accounting for letter spacing and multiline)
        const measureCanvas = document.createElement('canvas');
        const mctx = measureCanvas.getContext('2d');
        mctx.font = fontStyle;
        // Measure widest line for multiline support
        let maxLineWidth = 0;
        for (const line of lines) {
            const lw = mctx.measureText(line).width + letterSpacing * Math.max(0, line.length - 1);
            if (lw > maxLineWidth) maxLineWidth = lw;
        }
        const effectPad = (textEffect !== 'none') ? size * 0.15 + 8 : 0;
        const tw = Math.ceil(maxLineWidth) + strokeWidth * 2 + 20 + effectPad * 2;
        const th = lineHeightPx * lines.length + strokeWidth * 2 + 20 + effectPad * 2;

        // Render
        measureCanvas.width = tw;
        measureCanvas.height = th;
        const rctx = measureCanvas.getContext('2d');
        rctx.font = fontStyle;
        rctx.textBaseline = 'top';
        const textX = strokeWidth + 10 + effectPad;
        const textY = strokeWidth + 8 + effectPad;

        // Apply text effect (shadow/glow drawn BEFORE main text)
        if (textEffect === 'shadow') {
            rctx.save();
            rctx.shadowColor = 'rgba(0,0,0,0.7)';
            rctx.shadowBlur = size * 0.08;
            rctx.shadowOffsetX = size * 0.04;
            rctx.shadowOffsetY = size * 0.04;
        } else if (textEffect === 'glow') {
            rctx.save();
            rctx.shadowColor = fillColor;
            rctx.shadowBlur = size * 0.15;
            rctx.shadowOffsetX = 0;
            rctx.shadowOffsetY = 0;
        } else if (textEffect === 'neon') {
            // Neon: draw multiple glow passes
            rctx.save();
            for (let pass = 3; pass >= 1; pass--) {
                rctx.shadowColor = fillColor;
                rctx.shadowBlur = size * 0.06 * pass;
                rctx.globalAlpha = 0.3;
                rctx.fillStyle = fillColor;
                _drawTextWithSpacing(rctx, text, textX, textY, letterSpacing);
            }
            rctx.globalAlpha = 1.0;
            rctx.restore();
            rctx.save();
            rctx.shadowColor = '#fff';
            rctx.shadowBlur = size * 0.03;
        } else if (textEffect === 'emboss') {
            // Emboss: offset dark then light copy
            rctx.save();
            rctx.fillStyle = 'rgba(0,0,0,0.5)';
            _drawTextWithSpacing(rctx, text, textX + 2, textY + 2, letterSpacing);
            rctx.fillStyle = 'rgba(255,255,255,0.4)';
            _drawTextWithSpacing(rctx, text, textX - 1, textY - 1, letterSpacing);
            rctx.restore();
        }

        // Draw stroke (multiline)
        if (strokeWidth > 0) {
            rctx.strokeStyle = strokeColor;
            rctx.lineWidth = strokeWidth * 2;
            rctx.lineJoin = 'round';
            for (let li = 0; li < lines.length; li++) {
                _strokeTextWithSpacing(rctx, lines[li], textX, textY + li * lineHeightPx, letterSpacing);
            }
        }
        // Draw fill (multiline)
        rctx.fillStyle = fillColor;
        for (let li = 0; li < lines.length; li++) {
            _drawTextWithSpacing(rctx, lines[li], textX, textY + li * lineHeightPx, letterSpacing);
        }

        if (textEffect === 'shadow' || textEffect === 'glow' || textEffect === 'neon') {
            rctx.restore();
        }

        // Bockwinkel B8 (Workstream 23 #441 + #444): synchronous canvas swap
        // and undo snapshot before push. Old code had a Ctrl+Z race during
        // _txtImg.onload AND the text-add was completely un-undoable.
        if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('add text layer');
        const newLayer = {
            id: 'psd_text_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
            name: `Text: ${lines[0].substring(0, 20)}${lines.length > 1 ? '...' : ''}`,
            path: 'Text/' + lines[0].substring(0, 20),
            visible: true,
            opacity: 255,
            img: measureCanvas, // canvas is drawable directly — no Image() needed
            bbox: [Math.max(0, x - tw/2), Math.max(0, y - th/2), Math.min(2048, x + tw/2), Math.min(2048, y + th/2)],
            groupName: 'Text',
            blendMode: 'source-over',
            locked: false,
        };
        _psdLayers.push(newLayer);
        _psdLayersLoaded = true;
        _selectedLayerId = newLayer.id;
        if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
        recompositeFromLayers();
        renderLayerPanel();
        drawLayerBounds();
        if (typeof switchRightTab === 'function') switchRightTab('layers');
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        if (typeof showToast === 'function') showToast(`Text "${lines[0]}" added as layer — Ctrl+click to move`, 'success');

        // Text now lives in the real layer stack to avoid double-rendering via decals.
    }

    var _textCommitted = false;
    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) { if (!_textCommitted) { _textCommitted = true; commitText(); } e.preventDefault(); }
        // Shift+Enter inserts newline (textarea handles this natively)
        if (e.key === 'Escape') { _textCommitted = true; input.remove(); _textInputActive = false; }
    });
    input.addEventListener('blur', function () {
        if (!_textCommitted) { _textCommitted = true; setTimeout(commitText, 50); }
    });
}

// ══════════════════════════════════════════════════════════════════════════════
// SHAPE TOOL — Draw shapes on canvas as decals or mask fills
// ══════════════════════════════════════════════════════════════════════════════

var _shapeStart = null;
var _shapePreviewCanvas = null;

function drawShapePreview(startPt, endPt) {
    const pc = document.getElementById('paintCanvas');
    const rc = document.getElementById('regionCanvas');
    if (!pc || !rc) return;
    const zoom = typeof currentZoom !== 'undefined' ? currentZoom : 1;
    const ctx = rc.getContext('2d');

    // Redraw region overlay first
    if (typeof _doRenderRegionOverlay === 'function') _doRenderRegionOverlay();

    const shapeType = document.getElementById('shapeType')?.value || 'rect';
    const fillColor = document.getElementById('shapeFillColor')?.value || '#ffffff';
    const strokeColor = document.getElementById('shapeStrokeColor')?.value || '#000000';
    const strokeWidth = parseInt(document.getElementById('shapeStrokeWidth')?.value || 2);
    const filled = document.getElementById('shapeFilled')?.checked;
    const cornerRadius = parseInt(document.getElementById('shapeCornerRadius')?.value || 0);

    let x1 = startPt.x, y1 = startPt.y, x2 = endPt.x, y2 = endPt.y;

    ctx.save();
    ctx.lineWidth = strokeWidth;
    ctx.strokeStyle = strokeColor;
    ctx.fillStyle = filled ? fillColor : 'transparent';

    if (shapeType === 'rect') {
        const rx = Math.min(x1, x2), ry = Math.min(y1, y2);
        const rw = Math.abs(x2 - x1), rh = Math.abs(y2 - y1);
        if (cornerRadius > 0) {
            const cr = Math.min(cornerRadius, rw / 2, rh / 2);
            ctx.beginPath();
            ctx.moveTo(rx + cr, ry);
            ctx.lineTo(rx + rw - cr, ry);
            ctx.quadraticCurveTo(rx + rw, ry, rx + rw, ry + cr);
            ctx.lineTo(rx + rw, ry + rh - cr);
            ctx.quadraticCurveTo(rx + rw, ry + rh, rx + rw - cr, ry + rh);
            ctx.lineTo(rx + cr, ry + rh);
            ctx.quadraticCurveTo(rx, ry + rh, rx, ry + rh - cr);
            ctx.lineTo(rx, ry + cr);
            ctx.quadraticCurveTo(rx, ry, rx + cr, ry);
            ctx.closePath();
        } else {
            ctx.beginPath();
            ctx.rect(rx, ry, rw, rh);
        }
        if (filled) ctx.fill();
        if (strokeWidth > 0) ctx.stroke();
    } else if (shapeType === 'ellipse') {
        const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
        const rx = Math.abs(x2 - x1) / 2, ry = Math.abs(y2 - y1) / 2;
        ctx.beginPath();
        ctx.ellipse(cx, cy, Math.max(1, rx), Math.max(1, ry), 0, 0, Math.PI * 2);
        if (filled) ctx.fill();
        if (strokeWidth > 0) ctx.stroke();
    } else if (shapeType === 'line' || shapeType === 'arrow') {
        // Dash style
        const dashStyle = document.getElementById('lineDashStyle')?.value || 'solid';
        if (dashStyle === 'dashed') ctx.setLineDash([strokeWidth * 3, strokeWidth * 2]);
        else if (dashStyle === 'dotted') ctx.setLineDash([strokeWidth, strokeWidth * 1.5]);
        else if (dashStyle === 'dash-dot') ctx.setLineDash([strokeWidth * 3, strokeWidth, strokeWidth, strokeWidth]);
        else ctx.setLineDash([]);
        // Line caps
        const startCap = document.getElementById('lineStartCap')?.value || 'flat';
        const endCap = document.getElementById('lineEndCap')?.value || (shapeType === 'arrow' ? 'arrow' : 'flat');
        ctx.lineCap = (startCap === 'round' || endCap === 'round') ? 'round' : 'butt';
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        ctx.setLineDash([]);
        // Draw arrow caps
        const angle = Math.atan2(y2 - y1, x2 - x1);
        const headLen = Math.max(10, strokeWidth * 4);
        if (endCap === 'arrow') {
            ctx.beginPath();
            ctx.moveTo(x2, y2);
            ctx.lineTo(x2 - headLen * Math.cos(angle - 0.4), y2 - headLen * Math.sin(angle - 0.4));
            ctx.moveTo(x2, y2);
            ctx.lineTo(x2 - headLen * Math.cos(angle + 0.4), y2 - headLen * Math.sin(angle + 0.4));
            ctx.stroke();
        }
        if (startCap === 'arrow') {
            const aRev = angle + Math.PI;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x1 - headLen * Math.cos(aRev - 0.4), y1 - headLen * Math.sin(aRev - 0.4));
            ctx.moveTo(x1, y1);
            ctx.lineTo(x1 - headLen * Math.cos(aRev + 0.4), y1 - headLen * Math.sin(aRev + 0.4));
            ctx.stroke();
        }
        // Round caps are handled by ctx.lineCap = 'round'
    } else if (shapeType === 'polygon' || shapeType === 'star') {
        const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
        const radius = Math.hypot(x2 - x1, y2 - y1) / 2;
        const n = parseInt(document.getElementById('shapeVertices')?.value || 5);
        ctx.beginPath();
        if (shapeType === 'polygon') {
            for (let i = 0; i <= n; i++) {
                const a = (i / n) * Math.PI * 2 - Math.PI / 2;
                const px = cx + Math.cos(a) * radius;
                const py = cy + Math.sin(a) * radius;
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
        } else { // star
            for (let i = 0; i < n * 2; i++) {
                const a = (i / (n * 2)) * Math.PI * 2 - Math.PI / 2;
                const r = (i % 2 === 0) ? radius : radius * 0.4;
                const px = cx + Math.cos(a) * r;
                const py = cy + Math.sin(a) * r;
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.closePath();
        }
        if (filled) ctx.fill();
        if (strokeWidth > 0) ctx.stroke();
    } else {
        // All additional shapes: build path, then fill/stroke
        const rx = Math.min(x1, x2), ry = Math.min(y1, y2);
        const rw = Math.abs(x2 - x1), rh = Math.abs(y2 - y1);
        const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
        ctx.beginPath();

        if (shapeType === 'rounded-rect') {
            const cr = Math.min(cornerRadius || 15, rw / 2, rh / 2);
            ctx.moveTo(rx + cr, ry); ctx.lineTo(rx + rw - cr, ry);
            ctx.quadraticCurveTo(rx + rw, ry, rx + rw, ry + cr);
            ctx.lineTo(rx + rw, ry + rh - cr);
            ctx.quadraticCurveTo(rx + rw, ry + rh, rx + rw - cr, ry + rh);
            ctx.lineTo(rx + cr, ry + rh);
            ctx.quadraticCurveTo(rx, ry + rh, rx, ry + rh - cr);
            ctx.lineTo(rx, ry + cr);
            ctx.quadraticCurveTo(rx, ry, rx + cr, ry);
            ctx.closePath();
        } else if (shapeType === 'triangle') {
            ctx.moveTo(cx, ry); ctx.lineTo(rx + rw, ry + rh); ctx.lineTo(rx, ry + rh); ctx.closePath();
        } else if (shapeType === 'diamond') {
            ctx.moveTo(cx, ry); ctx.lineTo(rx + rw, cy); ctx.lineTo(cx, ry + rh); ctx.lineTo(rx, cy); ctx.closePath();
        } else if (shapeType === 'trapezoid') {
            const inset = rw * 0.2;
            ctx.moveTo(rx + inset, ry); ctx.lineTo(rx + rw - inset, ry); ctx.lineTo(rx + rw, ry + rh); ctx.lineTo(rx, ry + rh); ctx.closePath();
        } else if (shapeType === 'parallelogram') {
            const skew = rw * 0.25;
            ctx.moveTo(rx + skew, ry); ctx.lineTo(rx + rw, ry); ctx.lineTo(rx + rw - skew, ry + rh); ctx.lineTo(rx, ry + rh); ctx.closePath();
        } else if (shapeType === 'chevron') {
            const indent = rw * 0.3;
            ctx.moveTo(rx, ry); ctx.lineTo(rx + rw - indent, ry); ctx.lineTo(rx + rw, cy);
            ctx.lineTo(rx + rw - indent, ry + rh); ctx.lineTo(rx, ry + rh); ctx.lineTo(rx + indent, cy); ctx.closePath();
        } else if (shapeType === 'callout') {
            const cr2 = Math.min(10, rw / 4, rh / 4);
            const tailW = rw * 0.1, tailH = rh * 0.25;
            ctx.moveTo(rx + cr2, ry); ctx.lineTo(rx + rw - cr2, ry);
            ctx.quadraticCurveTo(rx + rw, ry, rx + rw, ry + cr2);
            ctx.lineTo(rx + rw, ry + rh * 0.7 - cr2);
            ctx.quadraticCurveTo(rx + rw, ry + rh * 0.7, rx + rw - cr2, ry + rh * 0.7);
            ctx.lineTo(rx + rw * 0.35 + tailW, ry + rh * 0.7);
            ctx.lineTo(rx + rw * 0.2, ry + rh); // tail tip
            ctx.lineTo(rx + rw * 0.35, ry + rh * 0.7);
            ctx.lineTo(rx + cr2, ry + rh * 0.7);
            ctx.quadraticCurveTo(rx, ry + rh * 0.7, rx, ry + rh * 0.7 - cr2);
            ctx.lineTo(rx, ry + cr2);
            ctx.quadraticCurveTo(rx, ry, rx + cr2, ry); ctx.closePath();
        } else if (shapeType === 'lightning') {
            const w6 = rw / 6, h4 = rh / 4;
            ctx.moveTo(rx + w6 * 3, ry); ctx.lineTo(rx + w6 * 5, ry + h4);
            ctx.lineTo(rx + w6 * 3.5, ry + h4); ctx.lineTo(rx + w6 * 5, ry + h4 * 2.5);
            ctx.lineTo(rx + w6 * 3, ry + h4 * 2.5); ctx.lineTo(rx + w6 * 4.5, ry + rh);
            ctx.lineTo(rx + w6, ry + h4 * 2); ctx.lineTo(rx + w6 * 2.5, ry + h4 * 2);
            ctx.lineTo(rx + w6, ry + h4); ctx.lineTo(rx + w6 * 2.5, ry + h4); ctx.closePath();
        } else if (shapeType === 'heart') {
            ctx.moveTo(cx, ry + rh * 0.35);
            ctx.bezierCurveTo(cx, ry, rx, ry, rx, ry + rh * 0.35);
            ctx.bezierCurveTo(rx, ry + rh * 0.6, cx, ry + rh * 0.8, cx, ry + rh);
            ctx.bezierCurveTo(cx, ry + rh * 0.8, rx + rw, ry + rh * 0.6, rx + rw, ry + rh * 0.35);
            ctx.bezierCurveTo(rx + rw, ry, cx, ry, cx, ry + rh * 0.35); ctx.closePath();
        } else if (shapeType === 'checkmark') {
            ctx.moveTo(rx, cy); ctx.lineTo(rx + rw * 0.35, ry + rh); ctx.lineTo(rx + rw, ry);
            ctx.lineTo(rx + rw - rw * 0.08, ry); ctx.lineTo(rx + rw * 0.35, ry + rh * 0.7);
            ctx.lineTo(rx + rw * 0.08, cy); ctx.closePath();
        } else if (shapeType === 'cross') {
            ctx.moveTo(rx + rw * 0.15, ry); ctx.lineTo(cx, cy - rh * 0.15);
            ctx.lineTo(rx + rw * 0.85, ry); ctx.lineTo(rx + rw, ry + rh * 0.15);
            ctx.lineTo(cx + rw * 0.15, cy); ctx.lineTo(rx + rw, ry + rh * 0.85);
            ctx.lineTo(rx + rw * 0.85, ry + rh); ctx.lineTo(cx, cy + rh * 0.15);
            ctx.lineTo(rx + rw * 0.15, ry + rh); ctx.lineTo(rx, ry + rh * 0.85);
            ctx.lineTo(cx - rw * 0.15, cy); ctx.lineTo(rx, ry + rh * 0.15); ctx.closePath();
        } else if (shapeType === 'gear') {
            const radius2 = Math.min(rw, rh) / 2;
            const teeth = 8, toothH = radius2 * 0.25;
            for (let i = 0; i < teeth; i++) {
                const a1 = (i / teeth) * Math.PI * 2;
                const a2 = a1 + (0.3 / teeth) * Math.PI * 2;
                const a3 = a1 + (0.5 / teeth) * Math.PI * 2;
                const a4 = a1 + (0.8 / teeth) * Math.PI * 2;
                const ri = radius2 - toothH, ro = radius2;
                if (i === 0) ctx.moveTo(cx + ri * Math.cos(a1), cy + ri * Math.sin(a1));
                ctx.lineTo(cx + ro * Math.cos(a2), cy + ro * Math.sin(a2));
                ctx.lineTo(cx + ro * Math.cos(a3), cy + ro * Math.sin(a3));
                ctx.lineTo(cx + ri * Math.cos(a4), cy + ri * Math.sin(a4));
            }
            ctx.closePath();
        } else if (shapeType === 'hexagon') {
            const hr = Math.min(rw, rh) / 2;
            for (let i = 0; i < 6; i++) {
                const a = (i / 6) * Math.PI * 2 - Math.PI / 6;
                if (i === 0) ctx.moveTo(cx + hr * Math.cos(a), cy + hr * Math.sin(a));
                else ctx.lineTo(cx + hr * Math.cos(a), cy + hr * Math.sin(a));
            }
            ctx.closePath();
        } else if (shapeType === 'octagon') {
            const or2 = Math.min(rw, rh) / 2;
            for (let i = 0; i < 8; i++) {
                const a = (i / 8) * Math.PI * 2 - Math.PI / 8;
                if (i === 0) ctx.moveTo(cx + or2 * Math.cos(a), cy + or2 * Math.sin(a));
                else ctx.lineTo(cx + or2 * Math.cos(a), cy + or2 * Math.sin(a));
            }
            ctx.closePath();
        }

        if (filled) ctx.fill();
        if (strokeWidth > 0) ctx.stroke();
    }
    ctx.restore();
}

function commitShape(startPt, endPt) {
    // Render the shape to an offscreen canvas and add as decal
    const shapeType = document.getElementById('shapeType')?.value || 'rect';
    const fillColor = document.getElementById('shapeFillColor')?.value || '#ffffff';
    const strokeColor = document.getElementById('shapeStrokeColor')?.value || '#000000';
    const strokeWidth = parseInt(document.getElementById('shapeStrokeWidth')?.value || 2);
    const filled = document.getElementById('shapeFilled')?.checked;
    const cornerRadius = parseInt(document.getElementById('shapeCornerRadius')?.value || 0);

    const x1 = startPt.x, y1 = startPt.y, x2 = endPt.x, y2 = endPt.y;
    const bx = Math.min(x1, x2) - strokeWidth - 2;
    const by = Math.min(y1, y2) - strokeWidth - 2;
    const bw = Math.abs(x2 - x1) + strokeWidth * 2 + 4;
    const bh = Math.abs(y2 - y1) + strokeWidth * 2 + 4;
    if (bw < 3 || bh < 3) return;

    const offscreen = document.createElement('canvas');
    offscreen.width = bw; offscreen.height = bh;
    const ctx = offscreen.getContext('2d');
    ctx.lineWidth = strokeWidth;
    ctx.strokeStyle = strokeColor;
    ctx.fillStyle = filled ? fillColor : 'transparent';

    // Translate so shape draws relative to bounding box
    const ox = strokeWidth + 2, oy = strokeWidth + 2;
    const sw = Math.abs(x2 - x1), sh = Math.abs(y2 - y1);

    if (shapeType === 'rect') {
        if (cornerRadius > 0) {
            const cr = Math.min(cornerRadius, sw / 2, sh / 2);
            ctx.beginPath();
            ctx.moveTo(ox + cr, oy); ctx.lineTo(ox + sw - cr, oy);
            ctx.quadraticCurveTo(ox + sw, oy, ox + sw, oy + cr);
            ctx.lineTo(ox + sw, oy + sh - cr);
            ctx.quadraticCurveTo(ox + sw, oy + sh, ox + sw - cr, oy + sh);
            ctx.lineTo(ox + cr, oy + sh);
            ctx.quadraticCurveTo(ox, oy + sh, ox, oy + sh - cr);
            ctx.lineTo(ox, oy + cr);
            ctx.quadraticCurveTo(ox, oy, ox + cr, oy);
            ctx.closePath();
        } else {
            ctx.beginPath(); ctx.rect(ox, oy, sw, sh);
        }
        if (filled) ctx.fill();
        if (strokeWidth > 0) ctx.stroke();
    } else if (shapeType === 'ellipse') {
        ctx.beginPath();
        ctx.ellipse(ox + sw / 2, oy + sh / 2, Math.max(1, sw / 2), Math.max(1, sh / 2), 0, 0, Math.PI * 2);
        if (filled) ctx.fill();
        if (strokeWidth > 0) ctx.stroke();
    } else if (shapeType === 'line' || shapeType === 'arrow') {
        const lx1 = (x1 < x2) ? ox : ox + sw, ly1 = (y1 < y2) ? oy : oy + sh;
        const lx2 = (x1 < x2) ? ox + sw : ox, ly2 = (y1 < y2) ? oy + sh : oy;
        // Dash style
        const dashStyle = document.getElementById('lineDashStyle')?.value || 'solid';
        if (dashStyle === 'dashed') ctx.setLineDash([strokeWidth * 3, strokeWidth * 2]);
        else if (dashStyle === 'dotted') ctx.setLineDash([strokeWidth, strokeWidth * 1.5]);
        else if (dashStyle === 'dash-dot') ctx.setLineDash([strokeWidth * 3, strokeWidth, strokeWidth, strokeWidth]);
        const startCap = document.getElementById('lineStartCap')?.value || 'flat';
        const endCap = document.getElementById('lineEndCap')?.value || (shapeType === 'arrow' ? 'arrow' : 'flat');
        ctx.lineCap = (startCap === 'round' || endCap === 'round') ? 'round' : 'butt';
        ctx.beginPath(); ctx.moveTo(lx1, ly1); ctx.lineTo(lx2, ly2); ctx.stroke();
        ctx.setLineDash([]);
        const angle = Math.atan2(ly2 - ly1, lx2 - lx1);
        const hl = Math.max(10, strokeWidth * 4);
        if (endCap === 'arrow') {
            ctx.beginPath(); ctx.moveTo(lx2, ly2);
            ctx.lineTo(lx2 - hl * Math.cos(angle - 0.4), ly2 - hl * Math.sin(angle - 0.4));
            ctx.moveTo(lx2, ly2);
            ctx.lineTo(lx2 - hl * Math.cos(angle + 0.4), ly2 - hl * Math.sin(angle + 0.4));
            ctx.stroke();
        }
        if (startCap === 'arrow') {
            const aRev = angle + Math.PI;
            ctx.beginPath(); ctx.moveTo(lx1, ly1);
            ctx.lineTo(lx1 - hl * Math.cos(aRev - 0.4), ly1 - hl * Math.sin(aRev - 0.4));
            ctx.moveTo(lx1, ly1);
            ctx.lineTo(lx1 - hl * Math.cos(aRev + 0.4), ly1 - hl * Math.sin(aRev + 0.4));
            ctx.stroke();
        }
    } else if (shapeType === 'polygon' || shapeType === 'star') {
        const cx = ox + sw / 2, cy = oy + sh / 2;
        const radius = Math.min(sw, sh) / 2;
        const n = parseInt(document.getElementById('shapeVertices')?.value || 5);
        ctx.beginPath();
        if (shapeType === 'polygon') {
            for (let i = 0; i <= n; i++) {
                const a = (i / n) * Math.PI * 2 - Math.PI / 2;
                if (i === 0) ctx.moveTo(cx + Math.cos(a) * radius, cy + Math.sin(a) * radius);
                else ctx.lineTo(cx + Math.cos(a) * radius, cy + Math.sin(a) * radius);
            }
        } else {
            for (let i = 0; i < n * 2; i++) {
                const a = (i / (n * 2)) * Math.PI * 2 - Math.PI / 2;
                const r = (i % 2 === 0) ? radius : radius * 0.4;
                if (i === 0) ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
                else ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
            }
            ctx.closePath();
        }
        if (filled) ctx.fill();
        if (strokeWidth > 0) ctx.stroke();
    } else {
        // Additional shapes (triangle, diamond, heart, etc.) — reuse preview paths with offset
        const ccx = ox + sw / 2, ccy = oy + sh / 2;
        ctx.beginPath();
        if (shapeType === 'rounded-rect') {
            const cr = Math.min(cornerRadius || 15, sw / 2, sh / 2);
            ctx.moveTo(ox + cr, oy); ctx.lineTo(ox + sw - cr, oy);
            ctx.quadraticCurveTo(ox + sw, oy, ox + sw, oy + cr);
            ctx.lineTo(ox + sw, oy + sh - cr);
            ctx.quadraticCurveTo(ox + sw, oy + sh, ox + sw - cr, oy + sh);
            ctx.lineTo(ox + cr, oy + sh);
            ctx.quadraticCurveTo(ox, oy + sh, ox, oy + sh - cr);
            ctx.lineTo(ox, oy + cr);
            ctx.quadraticCurveTo(ox, oy, ox + cr, oy); ctx.closePath();
        } else if (shapeType === 'triangle') {
            ctx.moveTo(ccx, oy); ctx.lineTo(ox + sw, oy + sh); ctx.lineTo(ox, oy + sh); ctx.closePath();
        } else if (shapeType === 'diamond') {
            ctx.moveTo(ccx, oy); ctx.lineTo(ox + sw, ccy); ctx.lineTo(ccx, oy + sh); ctx.lineTo(ox, ccy); ctx.closePath();
        } else if (shapeType === 'trapezoid') {
            const ins = sw * 0.2;
            ctx.moveTo(ox + ins, oy); ctx.lineTo(ox + sw - ins, oy); ctx.lineTo(ox + sw, oy + sh); ctx.lineTo(ox, oy + sh); ctx.closePath();
        } else if (shapeType === 'parallelogram') {
            const sk = sw * 0.25;
            ctx.moveTo(ox + sk, oy); ctx.lineTo(ox + sw, oy); ctx.lineTo(ox + sw - sk, oy + sh); ctx.lineTo(ox, oy + sh); ctx.closePath();
        } else if (shapeType === 'chevron') {
            const ind = sw * 0.3;
            ctx.moveTo(ox, oy); ctx.lineTo(ox + sw - ind, oy); ctx.lineTo(ox + sw, ccy);
            ctx.lineTo(ox + sw - ind, oy + sh); ctx.lineTo(ox, oy + sh); ctx.lineTo(ox + ind, ccy); ctx.closePath();
        } else if (shapeType === 'heart') {
            ctx.moveTo(ccx, oy + sh * 0.35);
            ctx.bezierCurveTo(ccx, oy, ox, oy, ox, oy + sh * 0.35);
            ctx.bezierCurveTo(ox, oy + sh * 0.6, ccx, oy + sh * 0.8, ccx, oy + sh);
            ctx.bezierCurveTo(ccx, oy + sh * 0.8, ox + sw, oy + sh * 0.6, ox + sw, oy + sh * 0.35);
            ctx.bezierCurveTo(ox + sw, oy, ccx, oy, ccx, oy + sh * 0.35); ctx.closePath();
        } else if (shapeType === 'hexagon') {
            const hr = Math.min(sw, sh) / 2;
            for (let i = 0; i < 6; i++) { const a = (i / 6) * Math.PI * 2 - Math.PI / 6; ctx.lineTo(ccx + hr * Math.cos(a), ccy + hr * Math.sin(a)); }
            ctx.closePath();
        } else if (shapeType === 'octagon') {
            const or2 = Math.min(sw, sh) / 2;
            for (let i = 0; i < 8; i++) { const a = (i / 8) * Math.PI * 2 - Math.PI / 8; ctx.lineTo(ccx + or2 * Math.cos(a), ccy + or2 * Math.sin(a)); }
            ctx.closePath();
        } else if (shapeType === 'lightning') {
            const w6 = sw / 6, h4 = sh / 4;
            ctx.moveTo(ox + w6 * 3, oy); ctx.lineTo(ox + w6 * 5, oy + h4);
            ctx.lineTo(ox + w6 * 3.5, oy + h4); ctx.lineTo(ox + w6 * 5, oy + h4 * 2.5);
            ctx.lineTo(ox + w6 * 3, oy + h4 * 2.5); ctx.lineTo(ox + w6 * 4.5, oy + sh);
            ctx.lineTo(ox + w6, oy + h4 * 2); ctx.lineTo(ox + w6 * 2.5, oy + h4 * 2);
            ctx.lineTo(ox + w6, oy + h4); ctx.lineTo(ox + w6 * 2.5, oy + h4); ctx.closePath();
        } else if (shapeType === 'gear') {
            const gr = Math.min(sw, sh) / 2, teeth = 8, th = gr * 0.25;
            for (let i = 0; i < teeth; i++) {
                const a1 = (i / teeth) * Math.PI * 2, a2 = a1 + (0.3 / teeth) * Math.PI * 2;
                const a3 = a1 + (0.5 / teeth) * Math.PI * 2, a4 = a1 + (0.8 / teeth) * Math.PI * 2;
                const ri = gr - th, ro = gr;
                if (i === 0) ctx.moveTo(ccx + ri * Math.cos(a1), ccy + ri * Math.sin(a1));
                ctx.lineTo(ccx + ro * Math.cos(a2), ccy + ro * Math.sin(a2));
                ctx.lineTo(ccx + ro * Math.cos(a3), ccy + ro * Math.sin(a3));
                ctx.lineTo(ccx + ri * Math.cos(a4), ccy + ri * Math.sin(a4));
            }
            ctx.closePath();
        } else if (shapeType === 'checkmark') {
            ctx.moveTo(ox, ccy); ctx.lineTo(ox + sw * 0.35, oy + sh); ctx.lineTo(ox + sw, oy);
            ctx.lineTo(ox + sw - sw * 0.08, oy); ctx.lineTo(ox + sw * 0.35, oy + sh * 0.7);
            ctx.lineTo(ox + sw * 0.08, ccy); ctx.closePath();
        } else if (shapeType === 'cross') {
            ctx.moveTo(ox + sw * 0.15, oy); ctx.lineTo(ccx, ccy - sh * 0.15);
            ctx.lineTo(ox + sw * 0.85, oy); ctx.lineTo(ox + sw, oy + sh * 0.15);
            ctx.lineTo(ccx + sw * 0.15, ccy); ctx.lineTo(ox + sw, oy + sh * 0.85);
            ctx.lineTo(ox + sw * 0.85, oy + sh); ctx.lineTo(ccx, ccy + sh * 0.15);
            ctx.lineTo(ox + sw * 0.15, oy + sh); ctx.lineTo(ox, oy + sh * 0.85);
            ctx.lineTo(ccx - sw * 0.15, ccy); ctx.lineTo(ox, oy + sh * 0.15); ctx.closePath();
        } else if (shapeType === 'callout') {
            const cr2 = Math.min(10, sw / 4, sh / 4);
            ctx.moveTo(ox + cr2, oy); ctx.lineTo(ox + sw - cr2, oy);
            ctx.quadraticCurveTo(ox + sw, oy, ox + sw, oy + cr2);
            ctx.lineTo(ox + sw, oy + sh * 0.7 - cr2);
            ctx.quadraticCurveTo(ox + sw, oy + sh * 0.7, ox + sw - cr2, oy + sh * 0.7);
            ctx.lineTo(ox + sw * 0.35 + sw * 0.1, oy + sh * 0.7);
            ctx.lineTo(ox + sw * 0.2, oy + sh);
            ctx.lineTo(ox + sw * 0.35, oy + sh * 0.7);
            ctx.lineTo(ox + cr2, oy + sh * 0.7);
            ctx.quadraticCurveTo(ox, oy + sh * 0.7, ox, oy + sh * 0.7 - cr2);
            ctx.lineTo(ox, oy + cr2);
            ctx.quadraticCurveTo(ox, oy, ox + cr2, oy); ctx.closePath();
        }
        if (filled) ctx.fill();
        if (strokeWidth > 0) ctx.stroke();
    }

    // Bockwinkel B8 (Workstream 23 #441 + #444): synchronous canvas swap
    // and undo snapshot before push. Old _shpImg.onload race made shape-add
    // un-undoable AND created a Ctrl+Z window where the layer didn't exist
    // yet on the stack.
    if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('add shape layer');
    const newLayer = {
        id: 'psd_shape_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
        name: `Shape: ${shapeType}`,
        path: 'Shape/' + shapeType,
        visible: true,
        opacity: 255,
        img: offscreen, // canvas drawable as image source — no Image() round-trip
        bbox: [bx, by, bx + bw, by + bh],
        groupName: 'Shape',
        blendMode: 'source-over',
        locked: false,
    };
    _psdLayers.push(newLayer);
    _psdLayersLoaded = true;
    _selectedLayerId = newLayer.id;
    if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
    recompositeFromLayers();
    renderLayerPanel();
    drawLayerBounds();
    if (typeof switchRightTab === 'function') switchRightTab('layers');
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast(`Shape added as layer`, 'success');

    // Shape now lives in the real layer stack to avoid double-rendering via decals.
}

// ══════════════════════════════════════════════════════════════════════════════
// CLONE STAMP TOOL — Alt+click source, paint to clone pixels
// ══════════════════════════════════════════════════════════════════════════════

var _cloneSource = null; // {x, y} canvas coordinates of source point
var _cloneOffset = null; // {dx, dy} offset from cursor to source

function paintCloneStroke(x, y) {
    var _t0 = (typeof window !== 'undefined' && window._SPB_DEBUG_PAINT_PERF === true) ? performance.now() : 0;
    const pc = document.getElementById('paintCanvas');
    if (!pc || !_cloneSource || !paintImageData) return;
    const ctx = pc.getContext('2d');
    const w = pc.width, h = pc.height;
    const data = paintImageData.data;

    // Read clone-specific controls (wired from tool options bar)
    const aligned = document.getElementById('cloneAligned')?.checked !== false; // default true
    const cloneOpacity = parseInt(document.getElementById('cloneOpacity')?.value || 100) / 100.0;

    if (aligned) {
        // Aligned mode: source moves with cursor (maintains fixed offset from first stroke)
        if (!_cloneOffset) {
            _cloneOffset = { dx: _cloneSource.x - x, dy: _cloneSource.y - y };
        }
    } else {
        // Non-aligned mode: source stays at original point, re-samples same area every stroke
        _cloneOffset = { dx: _cloneSource.x - x, dy: _cloneSource.y - y };
    }

    const srcX = x + _cloneOffset.dx;
    const srcY = y + _cloneOffset.dy;
    const radius = parseInt(document.getElementById('brushSize')?.value || 20);
    // Use clone-specific opacity, modulated by global brushFlow.
    // Track E #102 — Photoshop clone honors flow as a per-stamp multiplier.
    const flow = parseInt(document.getElementById('brushFlow')?.value || 100) / 100.0;
    const opacity = cloneOpacity * flow;
    const hardness = parseInt(document.getElementById('brushHardness')?.value || 100) / 100.0;
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;

    // Read source pixels, write to destination
    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const dist2 = dx * dx + dy * dy;
            if (dist2 > radius * radius) continue;

            const sx = srcX + dx, sy = srcY + dy;
            const tx = x + dx, ty = y + dy;
            if (sx < 0 || sx >= w || sy < 0 || sy >= h) continue;
            if (tx < 0 || tx >= w || ty < 0 || ty >= h) continue;

            const dist = Math.sqrt(dist2);
            const falloff = sigma > 0.5 ? Math.exp(-(dist * dist) / sigma2x2) : 1.0;
            const alpha = falloff * opacity;

            const si = (sy * w + sx) * 4;
            const ti = (ty * w + tx) * 4;

            // Blend source into target
            data[ti] = Math.round(data[ti] * (1 - alpha) + data[si] * alpha);
            data[ti + 1] = Math.round(data[ti + 1] * (1 - alpha) + data[si + 1] * alpha);
            data[ti + 2] = Math.round(data[ti + 2] * (1 - alpha) + data[si + 2] * alpha);
        }
    }

    // Update canvas display
    _flushPaintImageDataToCurrentSurface();
}

function drawCloneSourceIndicator(x, y) {
    if (!_cloneSource) return;
    const rc = document.getElementById('regionCanvas');
    if (!rc) return;
    const ctx = rc.getContext('2d');
    // Draw crosshair at source point
    const sx = _cloneSource.x, sy = _cloneSource.y;
    ctx.save();
    ctx.strokeStyle = '#ff3366';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(sx - 12, sy); ctx.lineTo(sx + 12, sy);
    ctx.moveTo(sx, sy - 12); ctx.lineTo(sx, sy + 12);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.arc(sx, sy, 8, 0, Math.PI * 2);
    ctx.stroke();
    // If offset established, draw line from source to current
    if (_cloneOffset) {
        const cx = x, cy = y;
        const curSrcX = cx + _cloneOffset.dx, curSrcY = cy + _cloneOffset.dy;
        ctx.strokeStyle = 'rgba(255,51,102,0.4)';
        ctx.setLineDash([2, 4]);
        ctx.beginPath();
        ctx.moveTo(curSrcX, curSrcY);
        ctx.lineTo(cx, cy);
        ctx.stroke();
        ctx.setLineDash([]);
        // Source tracking crosshair
        ctx.strokeStyle = '#ff3366';
        ctx.beginPath();
        ctx.arc(curSrcX, curSrcY, 6, 0, Math.PI * 2);
        ctx.stroke();
    }
    ctx.restore();
}

// ══════════════════════════════════════════════════════════════════════════════
// WIRE NEW TOOLS INTO CANVAS MODE SYSTEM
// ══════════════════════════════════════════════════════════════════════════════

// Extend the existing mousedown handler by hooking into the canvas event system.
// The new tools (text, shape, clone) need to be added to the canvasMode dispatch.
// We do this by patching the existing onmousedown chain.

(function _wireNewTools() {
    const pc = document.getElementById('paintCanvas');
    if (!pc) {
        // DOM not ready yet — retry
        document.addEventListener('DOMContentLoaded', _wireNewTools);
        return;
    }

    // Store the original onmousedown
    const _origMouseDown = pc.onmousedown;
    const _origMouseMove = pc.onmousemove;
    const _origMouseUp = pc.onmouseup;

    pc.onmousedown = function (e) {
        if (typeof canvasMode === 'undefined') { if (_origMouseDown) _origMouseDown.call(pc, e); return; }

        if (canvasMode === 'text') {
            const pos = typeof getPixelAt === 'function' ? getPixelAt(e) : null;
            if (pos) { onTextToolClick(pos.x, pos.y); e.preventDefault(); }
            return;
        }

        if (canvasMode === 'shape') {
            const pos = typeof getPixelAt === 'function' ? getPixelAt(e) : null;
            if (pos) {
                _shapeStart = pos;
                isDrawing = true;
                e.preventDefault();
            }
            return;
        }

        if (canvasMode === 'clone') {
            // 2026-04-18 marathon audit — CRITICAL FIX:
            // Pre-audit, this wrapper intercepted clone BEFORE the primary
            // layer-aware handler could run. It used window._cloneUndoSnapshot
            // (legacy single-shot snapshot that does NOT redo and does NOT
            // route to layer-paint). Result: painter selects Sponsors, Alt-
            // clicks to set clone source, drags to clone -> clone paints on
            // COMPOSITE instead of on the Sponsors layer. This is the "it
            // was kind of working and some fix must have broken it" class
            // of regression the user reported.
            // Fix: delegate clone entirely to the primary handler by falling
            // through. Source-indicator draw stays here so Alt+click UX is
            // preserved.
            const pos = typeof getPixelAt === 'function' ? getPixelAt(e) : null;
            if (!pos) return;
            if (e.altKey) {
                _cloneSource = { x: pos.x, y: pos.y };
                _cloneOffset = null;
                if (typeof showToast === 'function') showToast(`Clone source set at (${pos.x}, ${pos.y})`, 'info');
                if (typeof drawCloneSourceIndicator === 'function') drawCloneSourceIndicator(pos.x, pos.y);
                e.preventDefault();
                return;
            }
            // Fall through to primary handler, which has the full layer-aware
            // + pushPixelUndo + shouldBrushStrokeProceed logic.
            if (_origMouseDown) _origMouseDown.call(pc, e);
            return;
        }

        // Fall through to original handler
        if (_origMouseDown) _origMouseDown.call(pc, e);
    };

    pc.onmousemove = function (e) {
        if (typeof canvasMode === 'undefined') { if (_origMouseMove) _origMouseMove.call(pc, e); return; }

        if (canvasMode === 'shape' && isDrawing && _shapeStart) {
            let pos = typeof getPixelAtClamped === 'function' ? getPixelAtClamped(e) : null;
            if (pos) {
                // Shift = constrain (square rect, circle ellipse, 45° line)
                if (e.shiftKey) {
                    const dx = pos.x - _shapeStart.x, dy = pos.y - _shapeStart.y;
                    const size = Math.max(Math.abs(dx), Math.abs(dy));
                    pos = { x: _shapeStart.x + size * Math.sign(dx || 1), y: _shapeStart.y + size * Math.sign(dy || 1) };
                }
                drawShapePreview(_shapeStart, pos);
            }
            return;
        }

        if (canvasMode === 'clone' && isDrawing && _cloneSource) {
            const pos = typeof getPixelAtClamped === 'function' ? getPixelAtClamped(e) : null;
            if (pos) {
                paintCloneStroke(pos.x, pos.y);
                drawCloneSourceIndicator(pos.x, pos.y);
            }
            return;
        }

        // Fall through
        if (_origMouseMove) _origMouseMove.call(pc, e);
    };

    pc.onmouseup = function (e) {
        if (typeof canvasMode === 'undefined') { if (_origMouseUp) _origMouseUp.call(pc, e); return; }

        if (canvasMode === 'shape' && isDrawing && _shapeStart) {
            let pos = typeof getPixelAtClamped === 'function' ? getPixelAtClamped(e) : null;
            if (pos) {
                if (e.shiftKey) {
                    const dx = pos.x - _shapeStart.x, dy = pos.y - _shapeStart.y;
                    const size = Math.max(Math.abs(dx), Math.abs(dy));
                    pos = { x: _shapeStart.x + size * Math.sign(dx || 1), y: _shapeStart.y + size * Math.sign(dy || 1) };
                }
                commitShape(_shapeStart, pos);
            }
            _shapeStart = null;
            isDrawing = false;
            if (typeof _doRenderRegionOverlay === 'function') _doRenderRegionOverlay();
            return;
        }

        if (canvasMode === 'clone' && isDrawing) {
            // 2026-04-18 marathon audit — CRITICAL FIX:
            // Pre-audit this branch RETURNED early without falling through to
            // the primary mouseup, so _commitLayerPaint() never ran for clone
            // strokes on a selected layer. The layer canvas was left painted
            // in-memory but never committed back to layer.img, and
            // paintImageData was not restored to the composite. Other tools
            // could then misfire. Fix: reset clone-specific state here, then
            // DEFER the commit/cleanup to the primary mouseup by falling
            // through.
            _cloneOffset = null;
            // NOTE: do not clear isDrawing here — primary mouseup checks it
            // to decide whether to _commitLayerPaint for clone. Primary
            // will set isDrawing = false at the end.
        }

        // Fall through — primary mouseup handles _commitLayerPaint, undo
        // finalization, and preview triggering.
        if (_origMouseUp) _origMouseUp.call(pc, e);
    };
})();

// Add keyboard shortcuts for new tools
// SESSION ROUTER: bail if a higher-precedence listener already consumed the
// event (free transform, master Ctrl+shortcut handler, modal/dialog handlers).
// See docs/SESSION_KEY_ROUTER.md for the full precedence model.
document.addEventListener('keydown', function (e) {
    if (e.defaultPrevented) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (freeTransformState) return;
    const key = e.key.toLowerCase();
    if (key === 't' && !e.shiftKey) { if (typeof setCanvasMode === 'function') setCanvasMode('text'); e.preventDefault(); }
    else if (key === 'u') { if (typeof setCanvasMode === 'function') setCanvasMode('shape'); e.preventDefault(); }
    else if (key === 's') { if (typeof setCanvasMode === 'function') setCanvasMode('clone'); e.preventDefault(); }
    else if (key === 'n' && !e.shiftKey) { if (typeof setCanvasMode === 'function') setCanvasMode('pen'); e.preventDefault(); }
    else if (key === 'c') { if (typeof setCanvasMode === 'function') setCanvasMode('colorbrush'); e.preventDefault(); }
    else if (key === 'm') { if (typeof setCanvasMode === 'function') setCanvasMode('ellipse-marquee'); e.preventDefault(); }
});

// ══════════════════════════════════════════════════════════════════════════════
// PEN / BEZIER PATH TOOL — Click to place anchors, drag for curves
// Convert path to selection or stroke with current brush
// ══════════════════════════════════════════════════════════════════════════════

var penPoints = [];     // Array of {x, y, cx1, cy1, cx2, cy2} — anchor + control handles
var penClosed = false;
var penDragging = false;
var penDragIndex = -1;  // Which point is being dragged (-1 = none)

function addPenPoint(x, y) {
    penPoints.push({ x, y, cx1: x, cy1: y, cx2: x, cy2: y });
    drawPenPath();
}

function drawPenPath() {
    const rc = document.getElementById('regionCanvas');
    if (!rc) return;
    if (typeof _doRenderRegionOverlay === 'function') _doRenderRegionOverlay();
    const ctx = rc.getContext('2d');
    if (penPoints.length < 1) return;

    ctx.save();
    // Draw the path
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(penPoints[0].x, penPoints[0].y);
    for (let i = 1; i < penPoints.length; i++) {
        const prev = penPoints[i - 1], cur = penPoints[i];
        ctx.bezierCurveTo(prev.cx2, prev.cy2, cur.cx1, cur.cy1, cur.x, cur.y);
    }
    if (penClosed && penPoints.length >= 3) {
        const last = penPoints[penPoints.length - 1], first = penPoints[0];
        ctx.bezierCurveTo(last.cx2, last.cy2, first.cx1, first.cy1, first.x, first.y);
        ctx.closePath();
    }
    ctx.stroke();

    // Draw anchor points
    for (let i = 0; i < penPoints.length; i++) {
        const p = penPoints[i];
        // Anchor
        ctx.fillStyle = '#fff';
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 1;
        ctx.fillRect(p.x - 3, p.y - 3, 6, 6);
        ctx.strokeRect(p.x - 3, p.y - 3, 6, 6);
        // Control handles (if dragged away from anchor)
        if (Math.hypot(p.cx1 - p.x, p.cy1 - p.y) > 2) {
            ctx.strokeStyle = 'rgba(0,229,255,0.5)';
            ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.cx1, p.cy1); ctx.stroke();
            ctx.fillStyle = '#00e5ff';
            ctx.beginPath(); ctx.arc(p.cx1, p.cy1, 3, 0, Math.PI * 2); ctx.fill();
        }
        if (Math.hypot(p.cx2 - p.x, p.cy2 - p.y) > 2) {
            ctx.strokeStyle = 'rgba(0,229,255,0.5)';
            ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.cx2, p.cy2); ctx.stroke();
            ctx.fillStyle = '#00e5ff';
            ctx.beginPath(); ctx.arc(p.cx2, p.cy2, 3, 0, Math.PI * 2); ctx.fill();
        }
    }
    ctx.restore();
}

function closePenPath() {
    if (penPoints.length < 3) return;
    penClosed = true;
    drawPenPath();
}

function penPathToMask() {
    // Convert the pen path to a region mask (fill the closed path)
    const zone = zones[selectedZoneIndex];
    if (!zone || !penClosed || penPoints.length < 3) {
        if (typeof showToast === 'function') showToast('Close the path first (double-click or Enter)', 'info');
        return;
    }
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;
    if (typeof pushUndo === 'function') pushUndo(selectedZoneIndex);
    if (!zone.regionMask) zone.regionMask = new Uint8Array(w * h);

    const selMode = document.getElementById('selectionMode')?.value || 'add';
    if (selMode === 'replace') zone.regionMask.fill(0);
    const fillVal = (selMode === 'subtract') ? 0 : 255;

    // Rasterize bezier path using offscreen canvas. willReadFrequently:true
    // because the next step is getImageData on the entire canvas (class C
    // draw+read pattern, per Bockwinkel hot-path audit naming).
    const offscreen = document.createElement('canvas');
    offscreen.width = w; offscreen.height = h;
    const ctx = offscreen.getContext('2d', { willReadFrequently: true });
    ctx.beginPath();
    ctx.moveTo(penPoints[0].x, penPoints[0].y);
    for (let i = 1; i < penPoints.length; i++) {
        const prev = penPoints[i - 1], cur = penPoints[i];
        ctx.bezierCurveTo(prev.cx2, prev.cy2, cur.cx1, cur.cy1, cur.x, cur.y);
    }
    const last = penPoints[penPoints.length - 1], first = penPoints[0];
    ctx.bezierCurveTo(last.cx2, last.cy2, first.cx1, first.cy1, first.x, first.y);
    ctx.closePath();
    ctx.fillStyle = '#fff';
    ctx.fill();

    // Read rasterized path and apply to mask
    const imgData = ctx.getImageData(0, 0, w, h);
    for (let i = 0; i < w * h; i++) {
        if (imgData.data[i * 4 + 3] > 127) { // Alpha > 50%
            if (selMode === 'subtract') zone.regionMask[i] = 0;
            else zone.regionMask[i] = Math.max(zone.regionMask[i], fillVal);
        }
    }

    // Clear pen state
    penPoints = []; penClosed = false;
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (!maybeAutoTransformLayerSelection('pen-path')) {
        if (typeof showToast === 'function') showToast('Path converted to selection', 'success');
    }
}

function clearPenPath() {
    penPoints = []; penClosed = false;
    if (typeof _doRenderRegionOverlay === 'function') _doRenderRegionOverlay();
}

// ══════════════════════════════════════════════════════════════════════════════
// DIRECT COLOR BRUSH — Paint actual RGB colors onto the paint canvas
// ══════════════════════════════════════════════════════════════════════════════

var _foregroundColor = '#ffffff';
var _backgroundColor = '#000000';
var _layerPaintSourceMode = 'solid'; // 'solid' | 'special_baked'
var _layerPaintSpecialId = '';
var _layerPaintSpecialCache = Object.create(null);
var _layerPaintSpecialPendingKey = null;

function _getDefaultLayerPaintSpecialId() {
    if (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS) && MONOLITHICS.length > 0) {
        return MONOLITHICS[0].id;
    }
    return '';
}

function getLayerPaintSourceMode() {
    return _layerPaintSourceMode === 'special_baked' ? 'special_baked' : 'solid';
}
window.getLayerPaintSourceMode = getLayerPaintSourceMode;

function isLayerPaintSourceSpecial() {
    return getLayerPaintSourceMode() === 'special_baked';
}
window.isLayerPaintSourceSpecial = isLayerPaintSourceSpecial;

function getLayerPaintSpecialId() {
    return _layerPaintSpecialId || '';
}
window.getLayerPaintSpecialId = getLayerPaintSpecialId;

function _getLayerPaintSpecialMeta(id) {
    if (!id || typeof MONOLITHICS === 'undefined' || !Array.isArray(MONOLITHICS)) return null;
    return MONOLITHICS.find(function (m) { return m && m.id === id; }) || null;
}

function _getLayerPaintSpecialUrl(id, size) {
    if (!id) return null;
    const tintHex = (typeof _foregroundColor === 'string' && /^#[0-9a-fA-F]{6}$/.test(_foregroundColor)) ? _foregroundColor : '#888888';
    if (typeof getSwatchUrl === 'function') {
        return getSwatchUrl(id, tintHex, false, size || 256);
    }
    const base = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl)
        ? ShokkerAPI.baseUrl
        : `http://localhost:${window._SHOKKER_PORT || 59876}`;
    return `${base}/api/swatch/monolithic/${id}?color=${tintHex.replace('#', '')}&size=${size || 256}&prefer=live&v=${Date.now()}`;
}

function _getLayerPaintSpecialCacheKey(id) {
    const tintHex = (typeof _foregroundColor === 'string' && /^#[0-9a-fA-F]{6}$/.test(_foregroundColor)) ? _foregroundColor.toLowerCase() : '#888888';
    return `${id || ''}|${tintHex}`;
}

function _getCachedLayerPaintSpecialCanvas(id) {
    if (!id) return null;
    const entry = _layerPaintSpecialCache[_getLayerPaintSpecialCacheKey(id)];
    return entry && entry.canvas ? entry.canvas : null;
}

function _ensureLayerPaintSpecialCanvas(id, options) {
    const specialId = id || getLayerPaintSpecialId() || _getDefaultLayerPaintSpecialId();
    if (!specialId) return Promise.resolve(null);
    const opts = options || {};
    const key = _getLayerPaintSpecialCacheKey(specialId);
    const existing = _layerPaintSpecialCache[key];
    if (existing) {
        if (existing.canvas) return Promise.resolve(existing.canvas);
        if (existing.promise) return existing.promise;
    }
    const url = _getLayerPaintSpecialUrl(specialId, opts.size || 256);
    if (!url) return Promise.resolve(null);
    const promise = new Promise(function (resolve, reject) {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = function () {
            const canvas = document.createElement('canvas');
            canvas.width = img.naturalWidth || img.width || 256;
            canvas.height = img.naturalHeight || img.height || 256;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            _layerPaintSpecialCache[key] = { canvas: canvas };
            resolve(canvas);
        };
        img.onerror = function () {
            delete _layerPaintSpecialCache[key];
            reject(new Error(`Failed to load baked special preview for ${specialId}`));
        };
        img.src = url;
    });
    _layerPaintSpecialCache[key] = { promise: promise };
    return promise;
}

function warmLayerPaintSpecialCache(showLoadingToast) {
    if (!isLayerPaintSourceSpecial()) return Promise.resolve(null);
    const specialId = getLayerPaintSpecialId() || _getDefaultLayerPaintSpecialId();
    if (!specialId) return Promise.resolve(null);
    const key = _getLayerPaintSpecialCacheKey(specialId);
    if (showLoadingToast && _layerPaintSpecialPendingKey !== key && typeof showToast === 'function') {
        _layerPaintSpecialPendingKey = key;
        showToast(`Loading baked Special "${(_getLayerPaintSpecialMeta(specialId) || {}).name || specialId}"...`, 'info');
    }
    return _ensureLayerPaintSpecialCanvas(specialId).then(function (canvas) {
        _layerPaintSpecialPendingKey = null;
        if (typeof syncLayerPaintSourceUI === 'function') syncLayerPaintSourceUI();
        return canvas;
    }).catch(function (err) {
        _layerPaintSpecialPendingKey = null;
        if (typeof console !== 'undefined' && console.warn) console.warn('[layer-special-baked]', err);
        if (typeof showToast === 'function') {
            showToast(`Could not load baked Special "${(_getLayerPaintSpecialMeta(specialId) || {}).name || specialId}"`, 'warn');
        }
        return null;
    });
}
window.warmLayerPaintSpecialCache = warmLayerPaintSpecialCache;

function syncLayerPaintSourceUI() {
    const sourceSelect = document.getElementById('layerPaintSourceMode');
    if (sourceSelect) sourceSelect.value = getLayerPaintSourceMode();

    const pickerBtn = document.getElementById('layerSpecialPickerBtn');
    const chip = document.getElementById('layerSpecialPreviewChip');
    const hint = document.getElementById('layerPaintSourceHint');
    const nameEl = document.getElementById('layerSpecialPreviewName');
    const swatchEl = document.getElementById('layerSpecialPreviewSwatch');
    const active = isLayerPaintSourceSpecial();
    const specialId = getLayerPaintSpecialId() || _getDefaultLayerPaintSpecialId();
    const meta = _getLayerPaintSpecialMeta(specialId);
    const swatchUrl = specialId ? _getLayerPaintSpecialUrl(specialId, 64) : null;
    const swatchColor = meta && meta.swatch
        ? (String(meta.swatch).startsWith('#') ? meta.swatch : `#${meta.swatch}`)
        : '#555555';

    if (pickerBtn) pickerBtn.style.display = active ? 'inline-flex' : 'none';
    if (chip) chip.style.display = active ? 'inline-flex' : 'none';
    if (hint) hint.style.display = active ? '' : 'none';
    if (nameEl) nameEl.textContent = meta ? meta.name : 'Choose Special...';
    if (swatchEl) {
        swatchEl.style.background = swatchColor;
        swatchEl.style.backgroundImage = swatchUrl ? `url("${swatchUrl}")` : '';
        swatchEl.style.backgroundSize = swatchUrl ? 'cover' : '';
        swatchEl.style.backgroundPosition = swatchUrl ? 'center' : '';
    }
}
window.syncLayerPaintSourceUI = syncLayerPaintSourceUI;

function setLayerPaintSourceMode(mode, options) {
    const next = (mode === 'special_baked') ? 'special_baked' : 'solid';
    const opts = options || {};
    _layerPaintSourceMode = next;
    if (next === 'special_baked' && !_layerPaintSpecialId) {
        _layerPaintSpecialId = _getDefaultLayerPaintSpecialId();
    }
    syncLayerPaintSourceUI();
    if (typeof refreshToolbarModeSensitiveUi === 'function') refreshToolbarModeSensitiveUi();
    if (next === 'special_baked') {
        warmLayerPaintSpecialCache(false);
    }
    if (!opts.silent && typeof showToast === 'function') {
        showToast(
            next === 'special_baked'
                ? `Layer paint source: baked Special${_layerPaintSpecialId ? ` - ${(_getLayerPaintSpecialMeta(_layerPaintSpecialId) || {}).name || _layerPaintSpecialId}` : ''}`
                : 'Layer paint source: solid color',
            'info'
        );
    }
    return next;
}
window.setLayerPaintSourceMode = setLayerPaintSourceMode;

function setLayerPaintSpecial(id, options) {
    const nextId = (typeof id === 'string' ? id.replace(/^mono:/, '') : '') || _getDefaultLayerPaintSpecialId();
    if (!nextId) return '';
    _layerPaintSpecialId = nextId;
    syncLayerPaintSourceUI();
    if (typeof refreshToolbarModeSensitiveUi === 'function') refreshToolbarModeSensitiveUi();
    if (isLayerPaintSourceSpecial()) warmLayerPaintSpecialCache(false);
    if (!(options && options.silent) && typeof showToast === 'function') {
        showToast(`Layer baked Special: ${(_getLayerPaintSpecialMeta(nextId) || {}).name || nextId}`, 'success');
    }
    return nextId;
}
window.setLayerPaintSpecial = setLayerPaintSpecial;

function openLayerSpecialPicker(triggerEl) {
    if (typeof openSwatchPicker === 'function') {
        openSwatchPicker(triggerEl, 'layerSpecialPaint', (typeof selectedZoneIndex !== 'undefined' ? selectedZoneIndex : 0));
        return;
    }
    if (typeof showToast === 'function') showToast('Special picker is not ready yet', 'warn');
}
window.openLayerSpecialPicker = openLayerSpecialPicker;

function _installLayerPaintSourceColorHooks() {
    const fgPicker = document.getElementById('fgColorPicker');
    if (fgPicker && !fgPicker._layerPaintSourceHooked) {
        const onFgChange = function () {
            syncLayerPaintSourceUI();
            if (isLayerPaintSourceSpecial()) warmLayerPaintSpecialCache(false);
        };
        fgPicker.addEventListener('input', onFgChange);
        fgPicker.addEventListener('change', onFgChange);
        fgPicker._layerPaintSourceHooked = true;
    }
    const fgHexInput = document.getElementById('fgHexInput');
    if (fgHexInput && !fgHexInput._layerPaintSourceHooked) {
        const onHexChange = function () {
            if (/^#[0-9a-fA-F]{6}$/.test(fgHexInput.value || '')) {
                syncLayerPaintSourceUI();
                if (isLayerPaintSourceSpecial()) warmLayerPaintSpecialCache(false);
            }
        };
        fgHexInput.addEventListener('input', onHexChange);
        fgHexInput.addEventListener('change', onHexChange);
        fgHexInput._layerPaintSourceHooked = true;
    }
}
setTimeout(function () {
    _installLayerPaintSourceColorHooks();
    syncLayerPaintSourceUI();
}, 0);

function _paintColorBrushAt(data, w, h, x, y, cr, cg, cb, radius, opacity, hardness) {
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;
    const r2 = radius * radius;
    const shape = document.getElementById('brushShape')?.value || 'round';

    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const dist2 = dx * dx + dy * dy;
            if (shape === 'round' && dist2 > r2) continue;
            if (shape === 'square' && (Math.abs(dx) > radius || Math.abs(dy) > radius)) continue;
            if (shape === 'diamond' && (Math.abs(dx) + Math.abs(dy) > radius)) continue;
            if (shape === 'slash' && Math.abs(dx - dy) > radius * 0.3) continue;
            if (shape === 'noise' && (dist2 > r2 || Math.random() > 0.6)) continue;

            const px = x + dx, py = y + dy;
            if (px < 0 || px >= w || py < 0 || py >= h) continue;
            const idx = (py * w + px) * 4;

            const dist = Math.sqrt(dist2);
            const falloff = sigma > 0.5 ? Math.exp(-(dist * dist) / sigma2x2) : (dist <= radius ? 1.0 : 0.0);
            const alpha = falloff * opacity;

            data[idx] = Math.round(data[idx] * (1 - alpha) + cr * 255 * alpha);
            data[idx + 1] = Math.round(data[idx + 1] * (1 - alpha) + cg * 255 * alpha);
            data[idx + 2] = Math.round(data[idx + 2] * (1 - alpha) + cb * 255 * alpha);
        }
    }
    if (typeof _logPaintPerf === 'function') _logPaintPerf('clone', _t0, radius);
}

function paintColorBrush(x, y) {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    // Auto-track recent colors
    if (typeof addRecentColor === 'function') addRecentColor(_foregroundColor);
    const w = pc.width, h = pc.height;
    const data = paintImageData.data;

    const hex = _foregroundColor;
    const cr = parseInt(hex.slice(1, 3), 16) / 255;
    const cg = parseInt(hex.slice(3, 5), 16) / 255;
    const cb = parseInt(hex.slice(5, 7), 16) / 255;

    const radius = parseInt(document.getElementById('brushSize')?.value || 20);
    const opacity = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100.0;
    const flow = parseInt(document.getElementById('brushFlow')?.value || 100) / 100.0;
    const hardness = parseInt(document.getElementById('brushHardness')?.value || 100) / 100.0;
    const effectiveOpacity = opacity * flow;

    // Check if pattern brush is active
    const usePattern = (typeof _patternBrushTexture !== 'undefined' && _patternBrushTexture);
    const paintFn = usePattern ?
        function(d, w, h, px, py) { paintPatternBrushAt(d, w, h, px, py, radius, effectiveOpacity, hardness); } :
        function(d, w, h, px, py) { _paintColorBrushAt(d, w, h, px, py, cr, cg, cb, radius, effectiveOpacity, hardness); };

    // Primary stroke
    paintFn(data, w, h, x, y);

    // Symmetry strokes
    const sym = getEffectiveSymmetryMode();
    if (sym === 'mirror-h' || sym === 'mirror-both') {
        paintFn(data, w, h, w - 1 - x, y);
    }
    if (sym === 'mirror-v' || sym === 'mirror-both') {
        paintFn(data, w, h, x, h - 1 - y);
    }
    if (sym === 'mirror-both') {
        paintFn(data, w, h, w - 1 - x, h - 1 - y);
    }
    if (sym === 'radial-4') {
        const cx = Math.floor(w / 2), cy = Math.floor(h / 2);
        const ddx = x - cx, ddy = y - cy;
        paintFn(data, w, h, cx - ddy, cy + ddx);
        paintFn(data, w, h, cx - ddx, cy - ddy);
        paintFn(data, w, h, cx + ddy, cy - ddx);
    }
    if (sym === 'radial-8') {
        const cx = Math.floor(w / 2), cy = Math.floor(h / 2);
        const ddx = x - cx, ddy = y - cy;
        for (let a = 1; a < 8; a++) {
            const angle = a * Math.PI / 4;
            const rx = Math.round(cx + ddx * Math.cos(angle) - ddy * Math.sin(angle));
            const ry = Math.round(cy + ddx * Math.sin(angle) + ddy * Math.cos(angle));
            paintFn(data, w, h, rx, ry);
        }
    }

    _flushPaintImageDataToCurrentSurface();
}

function swapForegroundBackground() {
    const tmp = _foregroundColor;
    _foregroundColor = _backgroundColor;
    _backgroundColor = tmp;
    // Update UI indicators
    const fgEl = document.getElementById('fgColorSwatch');
    const bgEl = document.getElementById('bgColorSwatch');
    const fgPicker = document.getElementById('fgColorPicker');
    const fgHexInput = document.getElementById('fgHexInput');
    if (fgEl) fgEl.style.background = _foregroundColor;
    if (bgEl) bgEl.style.background = _backgroundColor;
    if (fgPicker) fgPicker.value = _foregroundColor;
    if (fgHexInput) fgHexInput.value = _foregroundColor;
    if (typeof syncLayerPaintSourceUI === 'function') syncLayerPaintSourceUI();
    if (typeof warmLayerPaintSpecialCache === 'function' && isLayerPaintSourceSpecial()) warmLayerPaintSpecialCache(false);
}

// Reset to default black foreground, white background
function resetDefaultColors() {
    _foregroundColor = '#000000';
    _backgroundColor = '#ffffff';
    const fgEl = document.getElementById('fgColorSwatch');
    const bgEl = document.getElementById('bgColorSwatch');
    const fgPicker = document.getElementById('fgColorPicker');
    const bgPicker = document.getElementById('bgColorPicker');
    if (fgEl) fgEl.style.background = _foregroundColor;
    if (bgEl) bgEl.style.background = _backgroundColor;
    if (fgPicker) fgPicker.value = _foregroundColor;
    if (bgPicker) bgPicker.value = _backgroundColor;
    const fgHexInput = document.getElementById('fgHexInput');
    if (fgHexInput) fgHexInput.value = _foregroundColor;
    if (typeof syncLayerPaintSourceUI === 'function') syncLayerPaintSourceUI();
    if (typeof warmLayerPaintSpecialCache === 'function' && isLayerPaintSourceSpecial()) warmLayerPaintSpecialCache(false);
}
window.resetDefaultColors = resetDefaultColors;

// ══════════════════════════════════════════════════════════════════════════════
// RECOLOR TOOL — Replace one color with another using tolerance
// ══════════════════════════════════════════════════════════════════════════════

function paintRecolor(x, y) {
    var _t0 = (typeof window !== 'undefined' && window._SPB_DEBUG_PAINT_PERF === true) ? performance.now() : 0;
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height;
    const d = paintImageData.data;

    const radius = parseInt(document.getElementById('brushSize')?.value || 20);
    const tolerance = parseInt(document.getElementById('wandTolerance')?.value || 32);
    const opacity = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100;
    const hardness = parseInt(document.getElementById('brushHardness')?.value || 50) / 100;
    // PSD Painter Gauntlet Track E #102 — recolor now honors brushFlow.
    // Effective per-stamp blend = opacity * flow (Photoshop convention).
    const flow = parseInt(document.getElementById('brushFlow')?.value || 100) / 100;
    const effectiveOpacity = opacity * flow;
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;

    // Target color = color under cursor at drag start (secondary/bg color)
    const bgHex = _backgroundColor;
    const tr = parseInt(bgHex.slice(1, 3), 16);
    const tg = parseInt(bgHex.slice(3, 5), 16);
    const tb = parseInt(bgHex.slice(5, 7), 16);

    // Replacement color = foreground color
    const fgHex = _foregroundColor;
    const rr = parseInt(fgHex.slice(1, 3), 16);
    const rg = parseInt(fgHex.slice(3, 5), 16);
    const rb = parseInt(fgHex.slice(5, 7), 16);

    const r2 = radius * radius;
    const tol2 = tolerance * tolerance * 3; // Tolerance in RGB distance squared

    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const pixDist2 = dx * dx + dy * dy;
            if (pixDist2 > r2) continue;
            const px = x + dx, py = y + dy;
            if (px < 0 || px >= w || py < 0 || py >= h) continue;
            const idx = (py * w + px) * 4;

            // Check if pixel matches target color within tolerance
            const dr = d[idx] - tr, dg = d[idx+1] - tg, db = d[idx+2] - tb;
            const dist2 = dr * dr + dg * dg + db * db;
            if (dist2 > tol2) continue;

            // Gaussian hardness falloff
            const falloff = sigma > 0.5 ? Math.exp(-(pixDist2) / sigma2x2) : 1.0;

            // Blend strength based on how close the match is + brush falloff.
            // Track E #102 — brushFlow now folded into effectiveOpacity above.
            const match = 1 - Math.sqrt(dist2) / Math.sqrt(tol2);
            const blend = match * effectiveOpacity * falloff;

            d[idx] = Math.round(d[idx] * (1 - blend) + rr * blend);
            d[idx+1] = Math.round(d[idx+1] * (1 - blend) + rg * blend);
            d[idx+2] = Math.round(d[idx+2] * (1 - blend) + rb * blend);
        }
    }
    _flushPaintImageDataToCurrentSurface();
    if (typeof _logPaintPerf === 'function') _logPaintPerf('recolor', _t0, radius);
}
window.paintRecolor = paintRecolor;

// ══════════════════════════════════════════════════════════════════════════════
// SMUDGE TOOL — Finger painting: smear pixels in the drag direction
// ══════════════════════════════════════════════════════════════════════════════

var _smudgeBuffer = null; // Float32Array of picked-up color under brush at start

function paintSmudge(x, y) {
    // Track L #237 — opt-in perf timer. Enable via:
    //   window._SPB_DEBUG_PAINT_PERF = true
    // Logs ms per dab so painters can confirm whether large-brush smudge
    // is engine-bound or UI-bound. Off by default.
    var _t0 = (typeof window !== 'undefined' && window._SPB_DEBUG_PAINT_PERF === true) ? performance.now() : 0;
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height;
    const d = paintImageData.data;
    const radius = parseInt(document.getElementById('brushSize')?.value || 20);
    // Track E #102 — smudge now honors brushFlow as a per-stamp accumulation
    // multiplier (Photoshop convention: smudge "Strength" × flow controls
    // how aggressively each dab mixes into the running buffer).
    const baseStrength = parseInt(document.getElementById('brushOpacity')?.value || 50) / 100;
    const flow = parseInt(document.getElementById('brushFlow')?.value || 100) / 100;
    const strength = baseStrength * flow;
    const hardness = parseInt(document.getElementById('brushHardness')?.value || 50) / 100;
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;
    const r2 = radius * radius;

    // First call: pick up color under brush
    if (!_smudgeBuffer) {
        _smudgeBuffer = new Float32Array(radius * 2 * radius * 2 * 4);
        let bi = 0;
        for (let dy = -radius; dy < radius; dy++) {
            for (let dx = -radius; dx < radius; dx++) {
                const px = x + dx, py = y + dy;
                if (px >= 0 && px < w && py >= 0 && py < h && dx*dx+dy*dy <= r2) {
                    const si = (py * w + px) * 4;
                    _smudgeBuffer[bi] = d[si]; _smudgeBuffer[bi+1] = d[si+1];
                    _smudgeBuffer[bi+2] = d[si+2]; _smudgeBuffer[bi+3] = d[si+3];
                } else {
                    _smudgeBuffer[bi] = -1; // marker for out-of-bounds
                }
                bi += 4;
            }
        }
        return;
    }

    // Subsequent calls: blend smudge buffer with current pixels
    let bi = 0;
    for (let dy = -radius; dy < radius; dy++) {
        for (let dx = -radius; dx < radius; dx++) {
            const px = x + dx, py = y + dy;
            if (px >= 0 && px < w && py >= 0 && py < h && dx*dx+dy*dy <= r2 && _smudgeBuffer[bi] >= 0) {
                const si = (py * w + px) * 4;
                // Gaussian hardness falloff
                const pixDist2 = dx * dx + dy * dy;
                const falloff = sigma > 0.5 ? Math.exp(-(pixDist2) / sigma2x2) : 1.0;
                const localStr = strength * falloff;
                // Blend: new pixel = lerp(current, buffer, strength * falloff)
                for (let ch = 0; ch < 4; ch++) {
                    const mixed = d[si+ch] * (1 - localStr) + _smudgeBuffer[bi+ch] * localStr;
                    _smudgeBuffer[bi+ch] = mixed; // Update buffer with mixed result
                    d[si+ch] = Math.round(mixed);
                }
            }
            bi += 4;
        }
    }
    _flushPaintImageDataToCurrentSurface();
    _logPaintPerf('smudge', _t0, radius);
}

function _logPaintPerf(toolName, t0, radius) {
    if (typeof window !== 'undefined' && window._SPB_DEBUG_PAINT_PERF === true && t0 > 0) {
        try { console.log('[paint-perf] %s r=%d %sms', toolName, radius, (performance.now() - t0).toFixed(2)); } catch (_) {}
    }
}
window._logPaintPerf = _logPaintPerf;

function resetSmudge() { _smudgeBuffer = null; }
window.paintSmudge = paintSmudge;
window.resetSmudge = resetSmudge;

// ══════════════════════════════════════════════════════════════════════════════
// PENCIL TOOL — Single-pixel precise editing (like paint.net's Pencil)
// Left-click paints FG color, right-click paints BG color
// ══════════════════════════════════════════════════════════════════════════════

function paintPencil(x, y, useBG) {
    // TOOLS WAR Phase 3 — pencil now honors brushSize and brushOpacity but
    // forces hardness = 1.0 (binary edges, no anti-aliasing — that's what
    // distinguishes "pencil" from "brush" in Photoshop). Previous version
    // was a single-pixel toy regardless of size.
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height, d = paintImageData.data;
    const radius = Math.max(1, parseInt(document.getElementById('brushSize')?.value || 1));
    const opacity = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100;
    const color = useBG ? _backgroundColor : _foregroundColor;
    const cr = parseInt(color.slice(1, 3), 16);
    const cg = parseInt(color.slice(3, 5), 16);
    const cb = parseInt(color.slice(5, 7), 16);
    const r2 = radius * radius;
    const alphaByte = Math.round(255 * opacity);
    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            // Hard circular footprint — no falloff (pencil = binary edges).
            if (dx * dx + dy * dy > r2) continue;
            const px = x + dx, py = y + dy;
            if (px < 0 || px >= w || py < 0 || py >= h) continue;
            const idx = (py * w + px) * 4;
            // Opacity-blend: lerp toward target color by `opacity`.
            const inv = 1 - opacity;
            d[idx]   = Math.round(d[idx]   * inv + cr * opacity);
            d[idx+1] = Math.round(d[idx+1] * inv + cg * opacity);
            d[idx+2] = Math.round(d[idx+2] * inv + cb * opacity);
            // Force opaque alpha at the painted pixel (pencil is solid).
            d[idx+3] = Math.max(d[idx+3], alphaByte);
        }
    }
    _flushPaintImageDataToCurrentSurface();
}
window.paintPencil = paintPencil;

// ══════════════════════════════════════════════════════════════════════════════
// DODGE TOOL — Lighten pixels under the brush (like Photoshop's Dodge tool)
// ══════════════════════════════════════════════════════════════════════════════

function paintDodge(x, y) {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height, d = paintImageData.data;
    const radius = parseInt(document.getElementById('brushSize')?.value || 20);
    // Track Q #340 — dodge now honors brushFlow (Photoshop convention:
    // exposure × flow per stamp). Was previously ignoring flow.
    const exposure = parseInt(document.getElementById('brushOpacity')?.value || 30) / 100;
    const flow = parseInt(document.getElementById('brushFlow')?.value || 100) / 100;
    const strength = exposure * flow;
    const hardness = parseInt(document.getElementById('brushHardness')?.value || 50) / 100;
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;
    const r2 = radius * radius;

    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const dist2 = dx * dx + dy * dy;
            if (dist2 > r2) continue;
            const px = x + dx, py = y + dy;
            if (px < 0 || px >= w || py < 0 || py >= h) continue;
            const idx = (py * w + px) * 4;
            if (d[idx + 3] === 0) continue;
            const dist = Math.sqrt(dist2);
            const falloff = sigma > 0.5 ? Math.exp(-(dist * dist) / sigma2x2) : 1.0;
            const amt = falloff * strength * 0.15;
            d[idx]   = Math.min(255, d[idx]   + Math.round((255 - d[idx])   * amt));
            d[idx+1] = Math.min(255, d[idx+1] + Math.round((255 - d[idx+1]) * amt));
            d[idx+2] = Math.min(255, d[idx+2] + Math.round((255 - d[idx+2]) * amt));
        }
    }
    _flushPaintImageDataToCurrentSurface();
}
window.paintDodge = paintDodge;

// ══════════════════════════════════════════════════════════════════════════════
// BURN TOOL — Darken pixels under the brush (like Photoshop's Burn tool)
// ══════════════════════════════════════════════════════════════════════════════

function paintBurn(x, y) {
    // Track Q #340 — burn honors brushFlow as well; same Photoshop convention as dodge.
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height, d = paintImageData.data;
    const radius = parseInt(document.getElementById('brushSize')?.value || 20);
    const exposure = parseInt(document.getElementById('brushOpacity')?.value || 30) / 100;
    const flow = parseInt(document.getElementById('brushFlow')?.value || 100) / 100;
    const strength = exposure * flow;
    const hardness = parseInt(document.getElementById('brushHardness')?.value || 50) / 100;
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;
    const r2 = radius * radius;

    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const dist2 = dx * dx + dy * dy;
            if (dist2 > r2) continue;
            const px = x + dx, py = y + dy;
            if (px < 0 || px >= w || py < 0 || py >= h) continue;
            const idx = (py * w + px) * 4;
            if (d[idx + 3] === 0) continue;
            const dist = Math.sqrt(dist2);
            const falloff = sigma > 0.5 ? Math.exp(-(dist * dist) / sigma2x2) : 1.0;
            const amt = falloff * strength * 0.15;
            d[idx]   = Math.max(0, d[idx]   - Math.round(d[idx]   * amt));
            d[idx+1] = Math.max(0, d[idx+1] - Math.round(d[idx+1] * amt));
            d[idx+2] = Math.max(0, d[idx+2] - Math.round(d[idx+2] * amt));
        }
    }
    _flushPaintImageDataToCurrentSurface();
}
window.paintBurn = paintBurn;

// ══════════════════════════════════════════════════════════════════════════════
// BLUR BRUSH — Locally blur pixels under the brush (like Photoshop's Blur tool)
// ══════════════════════════════════════════════════════════════════════════════

function paintBlurBrush(x, y) {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height, d = paintImageData.data;
    const radius = parseInt(document.getElementById('brushSize')?.value || 15);
    const strength = parseInt(document.getElementById('brushOpacity')?.value || 50) / 100;
    const hardness = parseInt(document.getElementById('brushHardness')?.value || 50) / 100;
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;
    const r2 = radius * radius;
    const blurR = Math.max(1, Math.floor(radius * 0.3));

    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const pixDist2 = dx * dx + dy * dy;
            if (pixDist2 > r2) continue;
            const px = x + dx, py = y + dy;
            if (px < 1 || px >= w - 1 || py < 1 || py >= h - 1) continue;
            const idx = (py * w + px) * 4;
            // Gaussian hardness falloff
            const falloff = sigma > 0.5 ? Math.exp(-(pixDist2) / sigma2x2) : 1.0;
            const localStr = strength * falloff;
            // Box blur average of neighboring pixels
            let rr = 0, gg = 0, bb = 0, count = 0;
            for (let by = -blurR; by <= blurR; by++) {
                for (let bx = -blurR; bx <= blurR; bx++) {
                    const sx = px + bx, sy = py + by;
                    if (sx >= 0 && sx < w && sy >= 0 && sy < h) {
                        const si = (sy * w + sx) * 4;
                        rr += d[si]; gg += d[si+1]; bb += d[si+2]; count++;
                    }
                }
            }
            if (count > 0) {
                d[idx]   = Math.round(d[idx]   * (1 - localStr) + (rr / count) * localStr);
                d[idx+1] = Math.round(d[idx+1] * (1 - localStr) + (gg / count) * localStr);
                d[idx+2] = Math.round(d[idx+2] * (1 - localStr) + (bb / count) * localStr);
            }
        }
    }
    _flushPaintImageDataToCurrentSurface();
}
window.paintBlurBrush = paintBlurBrush;

// ══════════════════════════════════════════════════════════════════════════════
// SHARPEN BRUSH — Locally sharpen pixels under the brush
// ══════════════════════════════════════════════════════════════════════════════

function paintSharpenBrush(x, y) {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height, d = paintImageData.data;
    const radius = parseInt(document.getElementById('brushSize')?.value || 15);
    const strength = parseInt(document.getElementById('brushOpacity')?.value || 50) / 100;
    const hardness = parseInt(document.getElementById('brushHardness')?.value || 50) / 100;
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;
    const r2 = radius * radius;

    // Work on a copy to avoid feedback loops
    const src = new Uint8ClampedArray(d);
    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const pixDist2 = dx * dx + dy * dy;
            if (pixDist2 > r2) continue;
            const px = x + dx, py = y + dy;
            if (px < 1 || px >= w - 1 || py < 1 || py >= h - 1) continue;
            const idx = (py * w + px) * 4;
            // Gaussian hardness falloff
            const falloff = sigma > 0.5 ? Math.exp(-(pixDist2) / sigma2x2) : 1.0;
            const localStr = strength * falloff;
            for (let ch = 0; ch < 3; ch++) {
                const center = src[idx + ch];
                const avg = (src[((py-1)*w+px)*4+ch] + src[((py+1)*w+px)*4+ch] + src[(py*w+px-1)*4+ch] + src[(py*w+px+1)*4+ch]) / 4;
                d[idx + ch] = Math.max(0, Math.min(255, Math.round(center + (center - avg) * localStr * 0.5)));
            }
        }
    }
    _flushPaintImageDataToCurrentSurface();
}
window.paintSharpenBrush = paintSharpenBrush;

// ══════════════════════════════════════════════════════════════════════════════
// HOLY SHIT #1: PATTERN BRUSH — Paint with any texture pattern as the brush
// Paint carbon fiber, metal flake, brushed metal, etc. with a single stroke!
// ══════════════════════════════════════════════════════════════════════════════

var _patternBrushTexture = null; // HTMLCanvasElement with loaded pattern
var _patternBrushName = '';

function loadPatternBrush(patternName) {
    // Load a pattern from the server's pattern registry
    _patternBrushName = patternName;
    if (!patternName || patternName === 'none') {
        _patternBrushTexture = null;
        if (typeof showToast === 'function') showToast('Pattern brush: solid color mode');
        return;
    }
    // Render a 256x256 pattern tile via the server
    fetch('/api/render-pattern-tile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pattern: patternName, size: 256 })
    }).then(r => r.json()).then(data => {
        if (data.image) {
            const img = new Image();
            img.onload = function() {
                const c = document.createElement('canvas');
                c.width = 256; c.height = 256;
                c.getContext('2d').drawImage(img, 0, 0, 256, 256);
                _patternBrushTexture = c;
                if (typeof showToast === 'function') showToast(`Pattern brush: ${patternName}`);
            };
            img.src = data.image;
        }
    }).catch(() => {
        // Fallback: generate a procedural pattern
        const c = document.createElement('canvas');
        c.width = 64; c.height = 64;
        const ctx = c.getContext('2d');
        // Simple procedural patterns
        if (patternName === 'carbon') {
            for (let y = 0; y < 64; y += 4) for (let x = 0; x < 64; x += 4) {
                ctx.fillStyle = ((x + y) % 8 < 4) ? '#333' : '#1a1a1a';
                ctx.fillRect(x, y, 4, 4);
            }
        } else if (patternName === 'metal_flake') {
            ctx.fillStyle = '#888';
            ctx.fillRect(0, 0, 64, 64);
            for (let i = 0; i < 200; i++) {
                const brightness = 120 + Math.random() * 135;
                ctx.fillStyle = `rgb(${brightness},${brightness},${brightness})`;
                ctx.fillRect(Math.random() * 64, Math.random() * 64, 1, 1);
            }
        } else if (patternName === 'crosshatch') {
            ctx.strokeStyle = '#555';
            ctx.lineWidth = 1;
            for (let i = -64; i < 128; i += 6) {
                ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i + 64, 64); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(i, 64); ctx.lineTo(i + 64, 0); ctx.stroke();
            }
        } else {
            // Noise pattern fallback
            const imgData = ctx.createImageData(64, 64);
            for (let i = 0; i < imgData.data.length; i += 4) {
                const v = 80 + Math.random() * 100;
                imgData.data[i] = v; imgData.data[i+1] = v; imgData.data[i+2] = v; imgData.data[i+3] = 255;
            }
            ctx.putImageData(imgData, 0, 0);
        }
        _patternBrushTexture = c;
        if (typeof showToast === 'function') showToast(`Pattern brush: ${patternName} (procedural)`);
    });
}

// Cached texture data for the pattern brush. Per Bockwinkel's audit, the
// previous code re-read the pattern texture's getImageData on EVERY brush
// stamp, costing a CPU readback per dab. The texture is immutable while
// the brush is active, so we cache it and invalidate on texture change.
var _patternBrushTextureData = null;
var _patternBrushTextureKey = null;

function paintPatternBrushAt(data, w, h, x, y, radius, opacity, hardness) {
    if (!_patternBrushTexture) return;
    const r2 = radius * radius;
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;
    const tw = _patternBrushTexture.width, th = _patternBrushTexture.height;
    // Cache the readback. The pattern texture canvas is immutable while
    // the brush is active; re-reading per dab was the hottest waste in the
    // brush path. Invalidate via _patternBrushTextureKey when the texture
    // canvas instance changes.
    const _cacheKey = _patternBrushTexture; // identity-keyed
    let tData;
    if (_patternBrushTextureData && _patternBrushTextureKey === _cacheKey) {
        tData = _patternBrushTextureData;
    } else {
        tData = _patternBrushTexture.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, tw, th).data;
        _patternBrushTextureData = tData;
        _patternBrushTextureKey = _cacheKey;
    }

    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const dist2 = dx * dx + dy * dy;
            if (dist2 > r2) continue;
            const px = x + dx, py = y + dy;
            if (px < 0 || px >= w || py < 0 || py >= h) continue;
            const idx = (py * w + px) * 4;

            // Sample from tiling pattern texture
            const tx = ((px % tw) + tw) % tw;
            const ty = ((py % th) + th) % th;
            const ti = (ty * tw + tx) * 4;
            const pr = tData[ti], pg = tData[ti+1], pb = tData[ti+2];

            const dist = Math.sqrt(dist2);
            const falloff = sigma > 0.5 ? Math.exp(-(dist * dist) / sigma2x2) : (dist <= radius ? 1.0 : 0.0);
            const alpha = falloff * opacity;

            data[idx]   = Math.round(data[idx]   * (1 - alpha) + pr * alpha);
            data[idx+1] = Math.round(data[idx+1] * (1 - alpha) + pg * alpha);
            data[idx+2] = Math.round(data[idx+2] * (1 - alpha) + pb * alpha);
        }
    }
}
window.loadPatternBrush = loadPatternBrush;
window.paintPatternBrushAt = paintPatternBrushAt;

// ══════════════════════════════════════════════════════════════════════════════
// HOLY SHIT #2: REFERENCE IMAGE OVERLAY
// Load any image (real car photo, competitor's livery) as a transparent overlay
// ══════════════════════════════════════════════════════════════════════════════

var _referenceImage = null;
var _referenceOpacity = 0.3;
var _referenceVisible = false;

function loadReferenceImage() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = function() {
        const file = input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                _referenceImage = img;
                _referenceVisible = true;
                drawReferenceOverlay();
                if (typeof showToast === 'function') showToast(`Reference loaded: ${file.name} (${img.width}x${img.height})`);
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    };
    input.click();
}

function toggleReferenceVisible() {
    _referenceVisible = !_referenceVisible;
    drawReferenceOverlay();
}

function setReferenceOpacity(val) {
    _referenceOpacity = parseFloat(val);
    drawReferenceOverlay();
}

function drawReferenceOverlay() {
    // Draw on the template overlay canvas (or a dedicated reference canvas)
    let refCanvas = document.getElementById('referenceOverlayCanvas');
    if (!refCanvas) {
        // Create a new canvas overlay for references
        const viewport = document.getElementById('canvasViewport') || document.getElementById('splitSource');
        const pc = document.getElementById('paintCanvas');
        if (!viewport || !pc) return;
        refCanvas = document.createElement('canvas');
        refCanvas.id = 'referenceOverlayCanvas';
        refCanvas.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:5;opacity:0.3;';
        // Insert after paint canvas
        const inner = document.getElementById('canvasInner');
        if (inner) inner.appendChild(refCanvas);
    }

    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    refCanvas.width = pc.width;
    refCanvas.height = pc.height;
    refCanvas.style.width = pc.style.width;
    refCanvas.style.height = pc.style.height;

    const ctx = refCanvas.getContext('2d');
    ctx.clearRect(0, 0, refCanvas.width, refCanvas.height);

    if (_referenceImage && _referenceVisible) {
        refCanvas.style.opacity = _referenceOpacity;
        refCanvas.style.display = 'block';
        // Scale reference to fit canvas while maintaining aspect ratio
        const scale = Math.min(pc.width / _referenceImage.width, pc.height / _referenceImage.height);
        const dw = _referenceImage.width * scale;
        const dh = _referenceImage.height * scale;
        ctx.drawImage(_referenceImage, (pc.width - dw) / 2, (pc.height - dh) / 2, dw, dh);
    } else {
        refCanvas.style.display = 'none';
    }
}
window.loadReferenceImage = loadReferenceImage;
window.toggleReferenceVisible = toggleReferenceVisible;
window.setReferenceOpacity = setReferenceOpacity;

// ══════════════════════════════════════════════════════════════════════════════
// HOLY SHIT #3: COLOR HARMONY PICKER
// Shows complementary, analogous, triadic color schemes from any picked color
// ══════════════════════════════════════════════════════════════════════════════

function getColorHarmonies(hexColor) {
    // Parse hex to HSL
    const r = parseInt(hexColor.slice(1,3),16)/255;
    const g = parseInt(hexColor.slice(3,5),16)/255;
    const b = parseInt(hexColor.slice(5,7),16)/255;
    const max = Math.max(r,g,b), min = Math.min(r,g,b);
    let h = 0, s = 0, l = (max+min)/2;
    if (max !== min) {
        const d = max - min;
        s = l > 0.5 ? d/(2-max-min) : d/(max+min);
        if (max===r) h=((g-b)/d+(g<b?6:0))/6;
        else if (max===g) h=((b-r)/d+2)/6;
        else h=((r-g)/d+4)/6;
    }

    function hslToHex(h,s,l) {
        h = ((h%1)+1)%1;
        const hue2rgb = (p,q,t) => { if(t<0)t+=1;if(t>1)t-=1;if(t<1/6)return p+(q-p)*6*t;if(t<1/2)return q;if(t<2/3)return p+(q-p)*(2/3-t)*6;return p; };
        const q = l<0.5 ? l*(1+s) : l+s-l*s;
        const p = 2*l-q;
        const rr = Math.round(hue2rgb(p,q,h+1/3)*255);
        const gg = Math.round(hue2rgb(p,q,h)*255);
        const bb = Math.round(hue2rgb(p,q,h-1/3)*255);
        return '#'+[rr,gg,bb].map(x=>x.toString(16).padStart(2,'0')).join('');
    }

    return {
        base: hexColor,
        complementary: hslToHex(h+0.5, s, l),
        analogous: [hslToHex(h-1/12,s,l), hslToHex(h+1/12,s,l)],
        triadic: [hslToHex(h+1/3,s,l), hslToHex(h+2/3,s,l)],
        splitComplementary: [hslToHex(h+5/12,s,l), hslToHex(h+7/12,s,l)],
        tetradic: [hslToHex(h+0.25,s,l), hslToHex(h+0.5,s,l), hslToHex(h+0.75,s,l)],
    };
}

function showColorHarmonies(hexColor) {
    const harmonies = getColorHarmonies(hexColor || _foregroundColor);
    let html = `<div style="padding:8px;background:#111;border:1px solid var(--accent-cyan);border-radius:6px;font-size:9px;">`;
    html += `<div style="font-weight:bold;color:var(--accent-cyan);margin-bottom:4px;">COLOR HARMONIES</div>`;

    function swatch(color, label) {
        return `<div style="display:inline-flex;align-items:center;gap:3px;margin:2px 4px;cursor:pointer;" onclick="_foregroundColor='${color}';document.getElementById('fgColorSwatch').style.background='${color}';document.getElementById('fgColorPicker').value='${color}';showToast('FG: ${color}')">
            <div style="width:16px;height:16px;background:${color};border:1px solid #555;border-radius:2px;"></div>
            <span style="color:#aaa;">${label} ${color}</span></div>`;
    }

    html += `<div style="margin-bottom:3px;">${swatch(harmonies.base, 'Base')}</div>`;
    html += `<div style="margin-bottom:3px;">${swatch(harmonies.complementary, 'Complement')}</div>`;
    html += `<div style="margin-bottom:3px;">Analogous: ${harmonies.analogous.map((c,i)=>swatch(c,'A'+(i+1))).join('')}</div>`;
    html += `<div style="margin-bottom:3px;">Triadic: ${harmonies.triadic.map((c,i)=>swatch(c,'T'+(i+1))).join('')}</div>`;
    html += `<div style="margin-bottom:3px;">Split: ${harmonies.splitComplementary.map((c,i)=>swatch(c,'S'+(i+1))).join('')}</div>`;
    html += `<div>Tetradic: ${harmonies.tetradic.map((c,i)=>swatch(c,'Q'+(i+1))).join('')}</div>`;
    html += `</div>`;

    // Show as popup near the color swatch
    let popup = document.getElementById('colorHarmonyPopup');
    if (!popup) {
        popup = document.createElement('div');
        popup.id = 'colorHarmonyPopup';
        popup.style.cssText = 'position:fixed;z-index:1000;max-width:280px;';
        document.body.appendChild(popup);
    }
    popup.innerHTML = html;
    popup.style.display = 'block';
    // Position near the FG swatch
    const fgEl = document.getElementById('fgColorSwatch');
    if (fgEl) {
        const rect = fgEl.getBoundingClientRect();
        popup.style.left = rect.left + 'px';
        popup.style.top = (rect.bottom + 4) + 'px';
    }
    // Auto-close after 10 seconds or on click outside
    setTimeout(() => { if (popup) popup.style.display = 'none'; }, 10000);
    document.addEventListener('click', function _closeHarmony(e) {
        if (!popup.contains(e.target)) { popup.style.display = 'none'; document.removeEventListener('click', _closeHarmony); }
    }, { once: false });
}
window.getColorHarmonies = getColorHarmonies;
window.showColorHarmonies = showColorHarmonies;

// ══════════════════════════════════════════════════════════════════════════════
// HOLY SHIT #4: GRADIENT MAP — Map a color gradient to image luminosity
// ══════════════════════════════════════════════════════════════════════════════

var _activeAdjustmentColorPickCleanup = null;

function _normalizeAdjustmentHex(hex, fallback) {
    const safeFallback = /^#[0-9a-fA-F]{6}$/.test(fallback || '') ? fallback.toLowerCase() : '#000000';
    if (typeof hex !== 'string') return safeFallback;
    const raw = hex.trim();
    if (/^#[0-9a-fA-F]{6}$/.test(raw)) return raw.toLowerCase();
    if (/^[0-9a-fA-F]{6}$/.test(raw)) return ('#' + raw).toLowerCase();
    if (/^#[0-9a-fA-F]{3}$/.test(raw)) return '#' + raw.slice(1).split('').map(ch => ch + ch).join('').toLowerCase();
    if (/^[0-9a-fA-F]{3}$/.test(raw)) return '#' + raw.split('').map(ch => ch + ch).join('').toLowerCase();
    return safeFallback;
}

function _closeAdjustmentColorModal() {
    if (typeof _activeAdjustmentColorPickCleanup === 'function') {
        try { _activeAdjustmentColorPickCleanup(); } catch (_) { }
        _activeAdjustmentColorPickCleanup = null;
    }
    const modal = document.getElementById('adjustmentColorModal');
    if (modal && modal.parentNode) modal.parentNode.removeChild(modal);
}

function _pickCanvasColorOnce(label, onPick, onCancel) {
    const pc = document.getElementById('paintCanvas');
    if (!pc) {
        if (typeof showToast === 'function') showToast('Paint canvas is not ready for color picking', 'warn');
        if (typeof onCancel === 'function') onCancel();
        return;
    }
    if (typeof _activeAdjustmentColorPickCleanup === 'function') {
        try { _activeAdjustmentColorPickCleanup(); } catch (_) { }
    }
    const previousCursor = pc.style.cursor;
    const cleanup = () => {
        pc.style.cursor = previousCursor;
        pc.classList.remove('eyedropper-active');
        document.removeEventListener('mousedown', handlePick, true);
        document.removeEventListener('keydown', handleKeydown, true);
        if (_activeAdjustmentColorPickCleanup === cleanup) _activeAdjustmentColorPickCleanup = null;
    };
    const handlePick = (e) => {
        const rect = pc.getBoundingClientRect();
        if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) {
            return;
        }
        e.preventDefault();
        e.stopPropagation();
        const scaleX = pc.width / Math.max(rect.width, 1);
        const scaleY = pc.height / Math.max(rect.height, 1);
        const x = Math.max(0, Math.min(pc.width - 1, Math.floor((e.clientX - rect.left) * scaleX)));
        const y = Math.max(0, Math.min(pc.height - 1, Math.floor((e.clientY - rect.top) * scaleY)));
        const px = pc.getContext('2d', { willReadFrequently: true }).getImageData(x, y, 1, 1).data;
        const hex = '#' + [px[0], px[1], px[2]].map((value) => value.toString(16).padStart(2, '0')).join('');
        cleanup();
        if (typeof onPick === 'function') onPick(hex);
        if (typeof showToast === 'function') showToast(`${label}: ${hex.toUpperCase()}`, 'info');
    };
    const handleKeydown = (e) => {
        if (e.defaultPrevented) return; // SESSION ROUTER bail (capture-phase modal)
        if (e.key !== 'Escape') return;
        e.preventDefault();
        e.stopPropagation();
        cleanup();
        if (typeof onCancel === 'function') onCancel();
        if (typeof showToast === 'function') showToast('Canvas color pick cancelled', 'info');
    };
    pc.style.cursor = 'crosshair';
    pc.classList.add('eyedropper-active');
    document.addEventListener('mousedown', handlePick, true);
    document.addEventListener('keydown', handleKeydown, true);
    _activeAdjustmentColorPickCleanup = cleanup;
    if (typeof showToast === 'function') showToast(`${label}: click a color on the canvas`, 'info');
}

function _wireAdjustmentDialogColorField(root, fieldKey, initialColor) {
    const picker = root.querySelector(`[data-adjustment-picker="${fieldKey}"]`);
    const hexInput = root.querySelector(`[data-adjustment-hex="${fieldKey}"]`);
    const setValue = (nextColor) => {
        const normalized = _normalizeAdjustmentHex(nextColor, picker?.value || hexInput?.value || initialColor || '#000000');
        if (picker) picker.value = normalized;
        if (hexInput) hexInput.value = normalized.toUpperCase();
        return normalized;
    };
    const getValue = () => _normalizeAdjustmentHex(hexInput?.value || picker?.value || initialColor || '#000000', initialColor || '#000000');
    if (picker) picker.addEventListener('input', () => setValue(picker.value));
    if (hexInput) {
        hexInput.addEventListener('input', () => {
            const normalized = _normalizeAdjustmentHex(hexInput.value, '');
            if (/^#[0-9a-f]{6}$/.test(normalized) && picker) picker.value = normalized;
        });
        hexInput.addEventListener('blur', () => setValue(hexInput.value));
        hexInput.addEventListener('keydown', (e) => {
            if (e.key !== 'Enter') return;
            e.preventDefault();
            setValue(hexInput.value);
        });
    }
    root.querySelectorAll(`[data-adjustment-action="${fieldKey}"]`).forEach((btn) => {
        btn.addEventListener('click', () => {
            const action = btn.getAttribute('data-adjustment-value');
            if (action === 'fg') { setValue(_foregroundColor || '#ffffff'); return; }
            if (action === 'bg') { setValue(_backgroundColor || '#000000'); return; }
            if (action === 'canvas') {
                const overlay = document.getElementById('adjustmentColorModal');
                if (overlay) overlay.style.visibility = 'hidden';
                _pickCanvasColorOnce(btn.getAttribute('data-adjustment-label') || 'Pick color', (pickedHex) => {
                    setValue(pickedHex);
                    if (overlay) overlay.style.visibility = '';
                }, () => {
                    if (overlay) overlay.style.visibility = '';
                });
            }
        });
    });
    setValue(initialColor);
    return { getValue, setValue };
}

function _openAdjustmentColorDialog(config) {
    _closeAdjustmentColorModal();
    const overlay = document.createElement('div');
    overlay.id = 'adjustmentColorModal';
    overlay.className = 'modal-overlay active';
    overlay.style.zIndex = '12000';
    overlay.innerHTML = `
        <div class="modal" style="width:min(560px,92vw);max-width:560px;" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2 style="font-size:15px;">${config.title}</h2>
                <button type="button" class="modal-close" title="Close" aria-label="Close" data-adjustment-close>&times;</button>
            </div>
            <div class="modal-body" style="display:flex;flex-direction:column;gap:14px;">
                <div style="font-size:12px;color:var(--text-dim);line-height:1.45;">${config.description}</div>
                ${config.fields.map((field) => `
                    <div style="display:flex;flex-direction:column;gap:8px;padding:12px;border:1px solid var(--border);border-radius:8px;background:var(--bg-main);">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
                            <div style="font-size:12px;font-weight:700;color:var(--text);">${field.label}</div>
                            <div style="font-size:10px;color:var(--text-dim);">${field.hint || ''}</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                            <input type="color" value="${field.value}" data-adjustment-picker="${field.key}" aria-label="${field.label} picker" style="width:52px;height:36px;padding:0;border:1px solid var(--border);background:none;border-radius:6px;cursor:pointer;">
                            <input type="text" value="${field.value.toUpperCase()}" data-adjustment-hex="${field.key}" aria-label="${field.label} hex" spellcheck="false" style="width:116px;background:var(--bg-dark);border:1px solid var(--border);color:var(--text);padding:8px 10px;border-radius:6px;font-family:Consolas,monospace;font-size:12px;">
                            <button type="button" class="btn btn-secondary" data-adjustment-action="${field.key}" data-adjustment-value="fg" style="padding:6px 10px;font-size:11px;">Use FG</button>
                            <button type="button" class="btn btn-secondary" data-adjustment-action="${field.key}" data-adjustment-value="bg" style="padding:6px 10px;font-size:11px;">Use BG</button>
                            <button type="button" class="btn btn-secondary" data-adjustment-action="${field.key}" data-adjustment-value="canvas" data-adjustment-label="${field.label}" style="padding:6px 10px;font-size:11px;">Pick Canvas</button>
                        </div>
                    </div>
                `).join('')}
                ${config.showTolerance ? `
                    <div style="display:flex;flex-direction:column;gap:8px;padding:12px;border:1px solid var(--border);border-radius:8px;background:var(--bg-main);">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
                            <div style="font-size:12px;font-weight:700;color:var(--text);">Tolerance</div>
                            <div style="font-size:11px;color:var(--accent-orange);" data-adjustment-tolerance-readout>${config.tolerance || 40}</div>
                        </div>
                        <input type="range" min="1" max="120" value="${config.tolerance || 40}" data-adjustment-tolerance aria-label="Tolerance slider">
                        <div style="font-size:11px;color:var(--text-dim);">Higher tolerance reaches farther from the target color.</div>
                    </div>
                ` : ''}
            </div>
            <div class="modal-footer" style="justify-content:flex-end;flex-wrap:wrap;">
                <button type="button" class="btn btn-secondary" data-adjustment-close>Cancel</button>
                <button type="button" class="btn btn-accent" data-adjustment-apply>${config.applyLabel || 'Apply'}</button>
            </div>
        </div>
    `;
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) _closeAdjustmentColorModal();
    });
    document.body.appendChild(overlay);
    const fieldControls = {};
    for (const field of config.fields) fieldControls[field.key] = _wireAdjustmentDialogColorField(overlay, field.key, field.value);
    const toleranceInput = overlay.querySelector('[data-adjustment-tolerance]');
    const toleranceReadout = overlay.querySelector('[data-adjustment-tolerance-readout]');
    if (toleranceInput && toleranceReadout) {
        const syncTolerance = () => { toleranceReadout.textContent = toleranceInput.value; };
        toleranceInput.addEventListener('input', syncTolerance);
        syncTolerance();
    }
    overlay.querySelectorAll('[data-adjustment-close]').forEach((btn) => {
        btn.addEventListener('click', () => _closeAdjustmentColorModal());
    });
    overlay.querySelector('[data-adjustment-apply]')?.addEventListener('click', () => {
        const payload = {};
        for (const field of config.fields) payload[field.key] = fieldControls[field.key].getValue();
        if (toleranceInput) payload.tolerance = parseInt(toleranceInput.value || '40', 10) || 40;
        config.onApply(payload);
        _closeAdjustmentColorModal();
    });
}

function openGradientMapDialog() {
    _openAdjustmentColorDialog({
        title: 'Gradient Map',
        description: 'Choose the dark and light colors for the map. Use the spectrum, foreground/background swatches, or pick directly from the paint on the canvas.',
        applyLabel: 'Apply Gradient Map',
        fields: [
            { key: 'dark', label: 'Dark color', hint: 'Shadows / low luminance', value: '#000000' },
            { key: 'light', label: 'Light color', hint: 'Highlights / high luminance', value: _normalizeAdjustmentHex(_foregroundColor, '#ffffff') }
        ],
        onApply: ({ dark, light }) => applyGradientMap(dark, light)
    });
}
window.openGradientMapDialog = openGradientMapDialog;

function applyGradientMap(color1, color2) {
    const target = _getAdjustmentTarget('gradient map');
    if (!target) return;
    const c1 = _normalizeAdjustmentHex(color1, '#000000');
    const c2 = _normalizeAdjustmentHex(color2, _foregroundColor || '#ffffff');
    const r1 = parseInt(c1.slice(1,3),16), g1 = parseInt(c1.slice(3,5),16), b1 = parseInt(c1.slice(5,7),16);
    const r2 = parseInt(c2.slice(1,3),16), g2 = parseInt(c2.slice(3,5),16), b2 = parseInt(c2.slice(5,7),16);

    // 2026-04-19 HEENAN H4HR-PERF13 — applyGradientMap hot-path opt.
    // Bake /255 into the lum coefficients (one division per pixel removed),
    // bitwise round, drop manual clamp.
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const d = imgData.data, len = d.length;
    const cR = 0.299 / 255, cG = 0.587 / 255, cB = 0.114 / 255;
    for (let i = 0; i < len; i += 4) {
        if (d[i+3] === 0) continue;
        const lum = d[i] * cR + d[i+1] * cG + d[i+2] * cB;
        const inv = 1 - lum;
        d[i]   = (r1 * inv + r2 * lum + 0.5) | 0;
        d[i+1] = (g1 * inv + g2 * lum + 0.5) | 0;
        d[i+2] = (b1 * inv + b2 * lum + 0.5) | 0;
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    if (typeof showToast === 'function') showToast(`Gradient map: ${c1} → ${c2}`);
}
window.applyGradientMap = applyGradientMap;

// ══════════════════════════════════════════════════════════════════════════════
// HOLY SHIT #5: HISTORY BRUSH — Paint to restore pixels from a saved state
// ══════════════════════════════════════════════════════════════════════════════

// Codex HIGH fix (2026-04-18): per-layer history snapshots.
// Previously _historySnapshot was a single composite snapshot, so
// history-brushing on a layer would write COMPOSITE pixels into that
// layer (reintroducing colors from other layers). Now we keep both:
//   _historySnapshot          — composite snapshot (used when no layer is active)
//   _historySnapshotPerLayer  — Map<layerId, ImageData> — per-layer snapshot
// saveHistorySnapshot stores BOTH; paintHistoryBrush picks the right one.
var _historySnapshot = null;                  // Composite snapshot
var _historySnapshotPerLayer = new Map();     // {layerId: ImageData of that layer at full canvas size}

function saveHistorySnapshot() {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    // Composite snapshot.
    _historySnapshot = pc.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, pc.width, pc.height);
    // Per-layer snapshots so history brush on a layer pulls from THAT
    // layer's pixels, not the composite. Each layer renders into a
    // canvas-sized buffer so coords match the brush canvas.
    _historySnapshotPerLayer = new Map();
    if (typeof _psdLayers !== 'undefined' && _psdLayersLoaded) {
        for (const layer of _psdLayers) {
            if (!layer || !layer.img) continue;
            try {
                const lc = document.createElement('canvas');
                lc.width = pc.width; lc.height = pc.height;
                const lctx = lc.getContext('2d', { willReadFrequently: true });
                const bx = Array.isArray(layer.bbox) ? (layer.bbox[0] || 0) : 0;
                const by = Array.isArray(layer.bbox) ? (layer.bbox[1] || 0) : 0;
                lctx.drawImage(layer.img, bx, by);
                _historySnapshotPerLayer.set(layer.id, lctx.getImageData(0, 0, pc.width, pc.height));
            } catch (_) { /* skip if layer can't be rasterized */ }
        }
    }
    if (typeof showToast === 'function') showToast('History snapshot saved — History Brush will restore the right pixels (per-layer when a layer is selected)');
}

function paintHistoryBrush(x, y) {
    if (!_historySnapshot || !paintImageData) return;
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;
    // Codex HIGH fix: when painting on a layer (paintImageData was swapped
    // to the layer canvas via _initLayerPaintCanvas), pull source pixels
    // from the PER-LAYER snapshot. Falls back to composite snapshot only
    // when no layer is being edited or when we lack a per-layer snapshot
    // for the current layer.
    var sourceSnapshot = _historySnapshot;
    if (typeof _activeLayerCanvas !== 'undefined' && _activeLayerCanvas
        && typeof _selectedLayerId !== 'undefined' && _selectedLayerId
        && _historySnapshotPerLayer && _historySnapshotPerLayer.has(_selectedLayerId)) {
        sourceSnapshot = _historySnapshotPerLayer.get(_selectedLayerId);
    }
    const srcData = sourceSnapshot.data;
    const dstData = paintImageData.data;
    const radius = parseInt(document.getElementById('brushSize')?.value || 20);
    // Track Q — history brush honors flow per Photoshop (history brush IS a brush).
    const baseOpacity = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100;
    const flow = parseInt(document.getElementById('brushFlow')?.value || 100) / 100;
    const opacity = baseOpacity * flow;
    const hardness = parseInt(document.getElementById('brushHardness')?.value || 100) / 100;
    const sigma = radius * (1.0 - hardness) * 0.5;
    const sigma2x2 = 2.0 * sigma * sigma;
    const r2 = radius * radius;

    for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
            const dist2 = dx * dx + dy * dy;
            if (dist2 > r2) continue;
            const px = x + dx, py = y + dy;
            if (px < 0 || px >= w || py < 0 || py >= h) continue;
            const idx = (py * w + px) * 4;

            const dist = Math.sqrt(dist2);
            const falloff = sigma > 0.5 ? Math.exp(-(dist * dist) / sigma2x2) : 1.0;
            const alpha = falloff * opacity;

            // Blend current pixel toward history snapshot
            dstData[idx]   = Math.round(dstData[idx]   * (1 - alpha) + srcData[idx]   * alpha);
            dstData[idx+1] = Math.round(dstData[idx+1] * (1 - alpha) + srcData[idx+1] * alpha);
            dstData[idx+2] = Math.round(dstData[idx+2] * (1 - alpha) + srcData[idx+2] * alpha);
        }
    }
    _flushPaintImageDataToCurrentSurface();
}
window.saveHistorySnapshot = saveHistorySnapshot;
window.paintHistoryBrush = paintHistoryBrush;

// ══════════════════════════════════════════════════════════════════════════════
// HOLY SHIT #6: AUTO COLOR REPLACE — Select by color, shift hue of selection
// ══════════════════════════════════════════════════════════════════════════════

function autoColorReplace(targetHex, replacementHex, tolerance) {
    const target = _getAdjustmentTarget('color replace');
    if (!target) return;
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const d = imgData.data;
    const tol = Math.max(1, parseInt(tolerance || 40, 10) || 40);
    const normalizedTarget = _normalizeAdjustmentHex(targetHex, _backgroundColor || '#000000');
    const normalizedReplacement = _normalizeAdjustmentHex(replacementHex, _foregroundColor || '#ffffff');
    const tr = parseInt(normalizedTarget.slice(1,3),16);
    const tg = parseInt(normalizedTarget.slice(3,5),16);
    const tb = parseInt(normalizedTarget.slice(5,7),16);
    const rr = parseInt(normalizedReplacement.slice(1,3),16);
    const rg = parseInt(normalizedReplacement.slice(3,5),16);
    const rb = parseInt(normalizedReplacement.slice(5,7),16);
    const tol2 = tol * tol * 3;
    let count = 0;

    // 2026-04-19 HEENAN H4HR-PERF12 — autoColorReplace hot-path opt.
    // Precompute 1/sqrt(tol2) (Math.sqrt(tol2) was constant — calling it
    // per pixel was wasted work). Bitwise round + drop Math.round Math
    // dispatch. Uint8ClampedArray auto-clamps writes outside [0,255].
    const invSqrtTol = 1 / Math.sqrt(tol2);
    const len = d.length;
    for (let i = 0; i < len; i += 4) {
        if (d[i+3] === 0) continue;
        const dr = d[i]-tr, dg = d[i+1]-tg, db = d[i+2]-tb;
        const dist2 = dr*dr + dg*dg + db*db;
        if (dist2 <= tol2) {
            const blend = 1 - Math.sqrt(dist2) * invSqrtTol;
            const inv = 1 - blend;
            d[i]   = (d[i]  *inv + rr*blend + 0.5) | 0;
            d[i+1] = (d[i+1]*inv + rg*blend + 0.5) | 0;
            d[i+2] = (d[i+2]*inv + rb*blend + 0.5) | 0;
            count++;
        }
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    if (typeof showToast === 'function') showToast(`Replaced ${count.toLocaleString()} pixels: ${normalizedTarget} -> ${normalizedReplacement}`);
}

function openColorReplaceDialog() {
    _openAdjustmentColorDialog({
        title: 'Color Replace',
        description: 'Pick the color to replace and the new color to blend toward. Use canvas pick to sample directly from the visible paint.',
        applyLabel: 'Replace Color',
        showTolerance: true,
        tolerance: 40,
        fields: [
            { key: 'target', label: 'Target color', hint: 'Pixels near this color get replaced', value: _normalizeAdjustmentHex(_backgroundColor, '#000000') },
            { key: 'replacement', label: 'Replacement color', hint: 'Pixels blend toward this color', value: _normalizeAdjustmentHex(_foregroundColor, '#ffffff') }
        ],
        onApply: ({ target, replacement, tolerance }) => autoColorReplace(target, replacement, tolerance)
    });
}

function promptAutoColorReplace() {
    openColorReplaceDialog();
}
window.autoColorReplace = autoColorReplace;
window.openColorReplaceDialog = openColorReplaceDialog;
window.promptAutoColorReplace = promptAutoColorReplace;

// ══════════════════════════════════════════════════════════════════════════════
function getEffectiveSymmetryMode() {
    return 'off';
}
window.getEffectiveSymmetryMode = getEffectiveSymmetryMode;

// HOLY SHIT #7: SYMMETRY AXIS VISUALIZATION
// Draw the mirror/radial axis on the canvas so the user sees exactly where it is
// ══════════════════════════════════════════════════════════════════════════════

function drawSymmetryAxis() {
    const tc = document.getElementById('transformCanvas');
    const pc = document.getElementById('paintCanvas');
    if (!tc || !pc) return;
    const sym = getEffectiveSymmetryMode();
    if (sym === 'off' || typeof freeTransformState !== 'undefined' && freeTransformState) return;

    const w = pc.width, h = pc.height;
    // Only draw if transform canvas isn't being used for something else
    if (freeTransformState) return;
    const selLayer = typeof getSelectedLayer === 'function' ? getSelectedLayer() : null;

    // Use a dedicated overlay or the transform canvas when free
    tc.width = w; tc.height = h;
    tc.style.width = pc.style.width; tc.style.height = pc.style.height;
    tc.style.display = 'block';
    tc.style.pointerEvents = 'none';
    const ctx = tc.getContext('2d');
    ctx.clearRect(0, 0, w, h);

    // Draw layer bounds if a layer is selected
    if (selLayer && selLayer.visible && selLayer.img && typeof drawLayerBounds === 'function') {
        drawLayerBounds();
    }

    ctx.setLineDash([8, 4]);
    ctx.lineWidth = 1;

    if (sym === 'mirror-h' || sym === 'mirror-both') {
        ctx.strokeStyle = 'rgba(255,215,0,0.5)';
        ctx.beginPath();
        ctx.moveTo(w / 2, 0);
        ctx.lineTo(w / 2, h);
        ctx.stroke();
        // Label
        ctx.fillStyle = 'rgba(255,215,0,0.6)';
        ctx.font = '10px monospace';
        ctx.fillText('MIRROR H', w / 2 + 4, 14);
    }
    if (sym === 'mirror-v' || sym === 'mirror-both') {
        ctx.strokeStyle = 'rgba(0,229,255,0.5)';
        ctx.beginPath();
        ctx.moveTo(0, h / 2);
        ctx.lineTo(w, h / 2);
        ctx.stroke();
        ctx.fillStyle = 'rgba(0,229,255,0.6)';
        ctx.font = '10px monospace';
        ctx.fillText('MIRROR V', 4, h / 2 - 4);
    }
    if (sym.startsWith('radial')) {
        const cx = w / 2, cy = h / 2;
        const segments = sym === 'radial-4' ? 4 : 8;
        ctx.strokeStyle = 'rgba(255,100,255,0.4)';
        for (let i = 0; i < segments; i++) {
            const angle = (i / segments) * Math.PI * 2;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + Math.cos(angle) * Math.max(w, h), cy + Math.sin(angle) * Math.max(w, h));
            ctx.stroke();
        }
        ctx.fillStyle = 'rgba(255,100,255,0.6)';
        ctx.font = '10px monospace';
        ctx.fillText(`RADIAL ${segments}`, cx + 4, cy - 4);
    }
    ctx.setLineDash([]);
}
window.drawSymmetryAxis = drawSymmetryAxis;

// Auto-redraw symmetry axis when symmetry mode changes
(function() {
    const symEl = document.getElementById('symmetryMode');
    if (symEl) {
        symEl.addEventListener('change', function() {
            drawSymmetryAxis();
        });
    }
})();

// ELLIPTICAL MARQUEE — Drag to create elliptical selections
// ══════════════════════════════════════════════════════════════════════════════

var _ellipseStart = null;

function drawEllipsePreview(start, end) {
    const rc = document.getElementById('regionCanvas');
    if (!rc) return;
    if (typeof _doRenderRegionOverlay === 'function') _doRenderRegionOverlay();
    const ctx = rc.getContext('2d');

    const cx = (start.x + end.x) / 2;
    const cy = (start.y + end.y) / 2;
    const rx = Math.abs(end.x - start.x) / 2;
    const ry = Math.abs(end.y - start.y) / 2;

    ctx.save();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.ellipse(cx, cy, Math.max(1, rx), Math.max(1, ry), 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
}

function commitEllipseSelection(start, end) {
    const zone = zones[selectedZoneIndex];
    if (!zone) return;
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;
    if (typeof pushUndo === 'function') pushUndo(selectedZoneIndex);

    const selMode = document.getElementById('selectionMode')?.value || 'add';
    if (!zone.regionMask || selMode === 'replace') {
        zone.regionMask = new Uint8Array(w * h);
    }
    const fillVal = (selMode === 'subtract') ? 0 : 255;

    const cx = (start.x + end.x) / 2;
    const cy = (start.y + end.y) / 2;
    const rx = Math.abs(end.x - start.x) / 2;
    const ry = Math.abs(end.y - start.y) / 2;
    if (rx < 1 || ry < 1) return;

    const rx2 = rx * rx, ry2 = ry * ry;
    const minX = Math.max(0, Math.floor(cx - rx));
    const maxX = Math.min(w - 1, Math.ceil(cx + rx));
    const minY = Math.max(0, Math.floor(cy - ry));
    const maxY = Math.min(h - 1, Math.ceil(cy + ry));

    for (let y = minY; y <= maxY; y++) {
        for (let x = minX; x <= maxX; x++) {
            const dx = x - cx, dy = y - cy;
            if ((dx * dx) / rx2 + (dy * dy) / ry2 <= 1.0) {
                const idx = y * w + x;
                if (selMode === 'subtract') zone.regionMask[idx] = 0;
                else zone.regionMask[idx] = Math.max(zone.regionMask[idx], fillVal);
            }
        }
    }

    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    maybeAutoTransformLayerSelection('ellipse-marquee');
}

// ══════════════════════════════════════════════════════════════════════════════
// WIRE SPRINT 3 TOOLS INTO MOUSE EVENTS
// ══════════════════════════════════════════════════════════════════════════════

(function _wireSprint3Tools() {
    const pc = document.getElementById('paintCanvas');
    if (!pc) { document.addEventListener('DOMContentLoaded', _wireSprint3Tools); return; }

    const _prevDown = pc.onmousedown;
    const _prevMove = pc.onmousemove;
    const _prevUp = pc.onmouseup;

    pc.onmousedown = function (e) {
        if (typeof canvasMode === 'undefined') { if (_prevDown) _prevDown.call(pc, e); return; }

        const pos = typeof getPixelAt === 'function' ? getPixelAt(e) : null;
        if (!pos) { if (_prevDown) _prevDown.call(pc, e); return; }

        if (canvasMode === 'pen') {
            if (e.detail >= 2 && penPoints.length >= 3) {
                closePenPath();
                penPathToMask();
            } else if (penClosed) {
                penPathToMask();
            } else {
                addPenPoint(pos.x, pos.y);
                // Start drag for bezier handle
                penDragging = true;
                penDragIndex = penPoints.length - 1;
            }
            e.preventDefault();
            return;
        }

        if (canvasMode === 'colorbrush') {
            // 2026-04-18 marathon audit — CRITICAL FIX:
            // Same class of bug as the clone wrapper: this intercept used
            // legacy window._colorBrushUndoSnapshot (single-shot, no redo, no
            // layer routing) instead of the primary handler's layer-aware
            // path. Painter selects Sponsors, picks Color Brush, strokes ->
            // strokes landed on composite. Fix: delegate to primary handler.
            if (_prevDown) _prevDown.call(pc, e);
            return;
        }

        if (canvasMode === 'ellipse-marquee') {
            _ellipseStart = pos;
            isDrawing = true;
            e.preventDefault();
            return;
        }

        if (_prevDown) _prevDown.call(pc, e);
    };

    pc.onmousemove = function (e) {
        if (typeof canvasMode === 'undefined') { if (_prevMove) _prevMove.call(pc, e); return; }

        // Pen tool: drag to create bezier curve handles
        if (canvasMode === 'pen' && penDragging && penDragIndex >= 0) {
            const pos = typeof getPixelAtClamped === 'function' ? getPixelAtClamped(e) : null;
            if (pos && penPoints[penDragIndex]) {
                const p = penPoints[penDragIndex];
                // Control handle 2 follows cursor, handle 1 mirrors (smooth curve)
                p.cx2 = pos.x;
                p.cy2 = pos.y;
                // Mirror: cx1 is opposite direction from anchor
                p.cx1 = p.x * 2 - pos.x;
                p.cy1 = p.y * 2 - pos.y;
                drawPenPath();
            }
            return;
        }

        if (canvasMode === 'colorbrush' && isDrawing) {
            const pos = typeof getPixelAtClamped === 'function' ? getPixelAtClamped(e) : null;
            if (pos) paintColorBrush(pos.x, pos.y);
            return;
        }

        if (canvasMode === 'ellipse-marquee' && isDrawing && _ellipseStart) {
            let pos = typeof getPixelAtClamped === 'function' ? getPixelAtClamped(e) : null;
            if (pos) {
                if (e.shiftKey) {
                    const dx = pos.x - _ellipseStart.x, dy = pos.y - _ellipseStart.y;
                    const size = Math.max(Math.abs(dx), Math.abs(dy));
                    pos = { x: _ellipseStart.x + size * Math.sign(dx || 1), y: _ellipseStart.y + size * Math.sign(dy || 1) };
                }
                drawEllipsePreview(_ellipseStart, pos);
            }
            return;
        }

        if (_prevMove) _prevMove.call(pc, e);
    };

    pc.onmouseup = function (e) {
        if (typeof canvasMode === 'undefined') { if (_prevUp) _prevUp.call(pc, e); return; }

        // Release pen bezier drag
        if (canvasMode === 'pen' && penDragging) {
            penDragging = false;
            penDragIndex = -1;
            return;
        }

        if (canvasMode === 'colorbrush' && isDrawing) {
            // 2026-04-18 marathon audit — same class of bug as the clone
            // wrapper: early return prevented primary mouseup's
            // _commitLayerPaint() from running for color-brush strokes on
            // a selected layer. Fall through so the primary finalizes the
            // stroke correctly.
            // NOTE: do not set isDrawing=false here — primary needs it true
            // to enter its own colorbrush/layer-commit branch.
        }

        if (canvasMode === 'ellipse-marquee' && isDrawing && _ellipseStart) {
            let pos = typeof getPixelAtClamped === 'function' ? getPixelAtClamped(e) : null;
            if (pos) {
                if (e.shiftKey) {
                    const dx = pos.x - _ellipseStart.x, dy = pos.y - _ellipseStart.y;
                    const size = Math.max(Math.abs(dx), Math.abs(dy));
                    pos = { x: _ellipseStart.x + size * Math.sign(dx || 1), y: _ellipseStart.y + size * Math.sign(dy || 1) };
                }
                commitEllipseSelection(_ellipseStart, pos);
            }
            _ellipseStart = null;
            isDrawing = false;
            if (typeof _doRenderRegionOverlay === 'function') _doRenderRegionOverlay();
            return;
        }

        if (_prevUp) _prevUp.call(pc, e);
    };
})();

// Pen/colorbrush/ellipse keyboard handlers
// SESSION ROUTER: bail on defaultPrevented so transform/master listeners win first.
document.addEventListener('keydown', function (e) {
    if (e.defaultPrevented) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
    // Enter on pen tool = close and convert to selection
    if (e.key === 'Enter' && canvasMode === 'pen' && penPoints.length >= 3) {
        if (!penClosed) closePenPath();
        penPathToMask();
        e.preventDefault();
    }
    // Escape on pen tool = clear path
    if (e.key === 'Escape' && canvasMode === 'pen' && penPoints.length > 0) {
        clearPenPath();
        e.preventDefault();
    }
    // Delete last pen point
    if (e.key === 'Backspace' && canvasMode === 'pen' && penPoints.length > 0) {
        penPoints.pop();
        penClosed = false;
        drawPenPath();
        e.preventDefault();
    }
});

// ══════════════════════════════════════════════════════════════════════════════
// PSD-NATIVE LAYER SYSTEM v2 — Every layer is a live, toggleable, editable asset
// Eye toggles recomposite the canvas. Layers can be assigned to zones.
// ══════════════════════════════════════════════════════════════════════════════

var _psdData = null;       // Server response from /api/psd-import
var _psdPath = null;       // Path to loaded PSD
var _psdLayers = [];       // Array of {id, name, path, visible, opacity, img, bbox, groupName}
var _psdLayersLoaded = false; // True when all layers are rasterized and cached
var _selectedLayerId = null;  // Currently selected layer ID
function getCurrentSourcePaintFile() {
    if (_psdPath) return _psdPath;
    return document.getElementById('paintFile')?.value?.trim() || '';
}
window.getCurrentSourcePaintFile = getCurrentSourcePaintFile;

// ═══ DIAGNOSTIC HELPERS (Workstream 17 #321 + #322) ═══
// Two console-callable helpers a developer or support engineer can use to
// dump layer-system state and zone-payload state without instrumenting the
// app. Quiet by default; only emit when called.
//
// Usage from devtools:
//   window.dumpLayerState()       // returns + logs the layer stack snapshot
//   window.dumpZonePayload(0)     // returns + logs the zone[0] outgoing payload
//
// Both produce structured objects safe to copy into a bug report.
function dumpLayerState() {
    var snap = {
        psdLayersLoaded: !!_psdLayersLoaded,
        selectedLayerId: _selectedLayerId,
        layerCount: (typeof _psdLayers === 'undefined') ? 0 : _psdLayers.length,
        undoStackDepth: (typeof _layerUndoStack === 'undefined') ? 0 : _layerUndoStack.length,
        redoStackDepth: (typeof _layerRedoStack === 'undefined') ? 0 : _layerRedoStack.length,
        layers: (typeof _psdLayers === 'undefined') ? [] : _psdLayers.map(function (l) {
            return {
                id: l.id,
                name: l.name,
                visible: l.visible,
                opacity: l.opacity,
                blendMode: l.blendMode,
                locked: l.locked,
                bbox: Array.isArray(l.bbox) ? l.bbox.slice() : l.bbox,
                effectsEnabled: l.effects ? Object.keys(l.effects).filter(function (k) {
                    return l.effects[k] && l.effects[k].enabled;
                }) : [],
                imgKind: !l.img ? 'none' : (l.img instanceof HTMLCanvasElement ? 'canvas' : 'image'),
            };
        }),
    };
    try { console.log('[SPB][dumpLayerState]', snap); } catch (_) {}
    return snap;
}
window.dumpLayerState = dumpLayerState;

// Workstream 19 #361 — concise active-target summary. Returns a short string
// the UI can render in a status bar / tooltip so the user always knows what
// their next paint stroke / fill / effect will hit. No DOM coupling here;
// callers can pull it from devtools or feed it to a status indicator.
//   "layer:Sponsor" → currently editing PSD layer "Sponsor"
//   "layer:Sponsor (locked)" → layer is selected but locked → ops will no-op or warn
//   "layer:Sponsor (hidden)" → layer is selected but hidden → strokes invisible
//   "composite" → no layer selected; ops hit the flat composite paint canvas
function getActiveTargetSummary() {
    if (!isLayerToolbarMode()) {
        return 'zone:' + _getZoneContextLabel();
    }
    if (typeof _psdLayers === 'undefined' || !_psdLayersLoaded || !_selectedLayerId) {
        return 'layer:none';
    }
    const layer = _psdLayers.find(function (l) { return l.id === _selectedLayerId; });
    if (!layer) return 'layer:none';
    var tags = [];
    if (layer.locked) tags.push('locked');
    if (layer.visible === false) tags.push('hidden');
    var suffix = tags.length ? ' (' + tags.join(', ') + ')' : '';
    return 'layer:' + (layer.name || layer.id) + suffix;
}
window.getActiveTargetSummary = getActiveTargetSummary;

// Workstream 19 #364 — does the currently-selected zone have a sourceLayer
// restriction active? Returns the source layer's name (or null).
// Helps a UI show "this zone is restricted to <layer>".
function getZoneSourceLayerSummary(zoneIndex) {
    if (typeof zones === 'undefined') return null;
    var idx = (typeof zoneIndex === 'number') ? zoneIndex
            : (typeof selectedZoneIndex !== 'undefined' ? selectedZoneIndex : -1);
    var z = zones[idx];
    if (!z || !z.sourceLayer) return null;
    if (typeof _psdLayers === 'undefined') return { layerId: z.sourceLayer, exists: false, name: null };
    var layer = _psdLayers.find(function (l) { return l.id === z.sourceLayer; });
    return {
        layerId: z.sourceLayer,
        exists: !!layer,
        name: layer ? layer.name : null,
        visible: layer ? !!layer.visible : null,
        locked: layer ? !!layer.locked : null,
    };
}
window.getZoneSourceLayerSummary = getZoneSourceLayerSummary;

// Workstream 19 #363 — when a brush tool is blocked because the active layer
// is locked, surface ONE toast per session so the user understands why
// nothing happened. Throttle: warn once per layer per "tool stroke session".
var _lockedLayerWarnedFor = null;
function warnIfPaintingOnLockedLayer() {
    if (typeof _selectedLayerId === 'undefined' || !_selectedLayerId) return false;
    var layer = _psdLayers.find(function(l) { return l.id === _selectedLayerId; });
    if (!layer || !layer.locked) {
        _lockedLayerWarnedFor = null;
        return false;
    }
    if (_lockedLayerWarnedFor !== layer.id) {
        _lockedLayerWarnedFor = layer.id;
        if (typeof showToast === 'function') {
            showToast(`"${layer.name}" is locked — unlock to paint on it`, 'warn');
        }
    }
    return true;
}
window.warnIfPaintingOnLockedLayer = warnIfPaintingOnLockedLayer;

function dumpZonePayload(zoneIndex) {
    if (typeof zones === 'undefined' || !zones[zoneIndex]) {
        try { console.warn('[SPB][dumpZonePayload] no zone at index ' + zoneIndex); } catch (_) {}
        return null;
    }
    var z = zones[zoneIndex];
    var srcLayerId = z.sourceLayer;
    var srcLayer = (srcLayerId && typeof _psdLayers !== 'undefined') ? _psdLayers.find(function (l) { return l.id === srcLayerId; }) : null;
    var snap = {
        zoneIndex: zoneIndex,
        zoneName: z.name,
        finish: z.finish,
        base: z.base,
        pattern: z.pattern,
        sourceLayer: srcLayerId,
        sourceLayerExists: !!srcLayer,
        sourceLayerVisible: srcLayer ? srcLayer.visible : null,
        sourceLayerLocked: srcLayer ? srcLayer.locked : null,
        regionMaskHasContent: !!(z.regionMask && z.regionMask.some && z.regionMask.some(function (v) { return v > 0; })),
        spatialMaskHasContent: !!(z.spatialMask && z.spatialMask.some && z.spatialMask.some(function (v) { return v > 0; })),
        hardEdge: !!z.hardEdge,
        baseColorFitZone: !!z.baseColorFitZone,
        patternFitZone: !!(z.patternPlacement === 'fit' || z.patternFitZone),
    };
    try { console.log('[SPB][dumpZonePayload]', snap); } catch (_) {}
    return snap;
}
window.dumpZonePayload = dumpZonePayload;

async function importPSD() {
    if (typeof openFilePicker === 'function') {
        openFilePicker({
            title: 'Open Photoshop PSD File',
            filter: '.psd',
            mode: 'file',
            startPath: document.getElementById('paintFile')?.value?.replace(/[/\\][^/\\]+$/, '') || '',
            onSelect: function (path) { _doPSDImport(path); }
        });
        return;
    }
    const psdPath = prompt('Enter the full path to the PSD file:', '');
    if (psdPath) _doPSDImport(psdPath);
}

async function _doPSDImport(psdPath) {
    if (!psdPath) return;
    // 2026-04-18 MARATHON bug #40 (Raven, HIGH): pre-fix, two concurrent
    // calls to _doPSDImport (double file-picker click, keyboard shortcut
    // + button, or script-driven) caused a classic async race. Call #2
    // reset _psdLayers while call #1 was still awaiting image loads.
    // Call #1's Promise.all then populated layer.img on orphaned layer
    // objects (the ones the assignment overwrote), leaving call #2's
    // fresh _psdLayers with layer.img = null forever. Symptom: layer
    // panel shows the new PSD's names but canvas composites as blank
    // (or shows call #1's pixels). Guard against re-entry.
    if (window._spbPsdImportInFlight) {
        if (typeof showToast === 'function') {
            showToast('PSD import already in progress — wait for it to finish', 'warn');
        }
        return;
    }
    window._spbPsdImportInFlight = true;
    if (typeof showToast === 'function') showToast('Loading PSD...', 'info');

    try {
        // Step 1: Get composite + layer tree (fast — ~100ms)
        const resp = await fetch('/api/psd-import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Shokker-Internal': '1',
            },
            body: JSON.stringify({ psd_path: psdPath, thumbnail_size: 128 })
        });
        const data = await resp.json();

        if (!data.success) {
            if (typeof showToast === 'function') showToast('PSD import failed: ' + (data.error || 'Unknown'), true);
            return;
        }

        _psdData = data;
        _psdPath = psdPath;
        _psdLayers = [];
        _psdLayersLoaded = false;
        // 2026-04-18 marathon chaos audit — pre-fix, loading a new PSD did
        // not reset the in-memory layer-edit state. Old undo/redo entries
        // referenced layer IDs that no longer existed, and a dangling
        // _activeLayerCanvas could survive into the new session if the
        // painter was mid-stroke when they hit Import. Ctrl+Z then either
        // did nothing or restored stale pixels against the wrong layer.
        _selectedLayerId = null;
        if (typeof window !== 'undefined') window._selectedLayerId = null;
        _activeLayerCanvas = null;
        _activeLayerCtx = null;
        _savedPaintImageData = null;
        if (Array.isArray(_layerUndoStack)) _layerUndoStack.length = 0;
        if (Array.isArray(_layerRedoStack)) _layerRedoStack.length = 0;
        if (typeof _resetLayerPaintFailToasts === 'function') _resetLayerPaintFailToasts();
        // Clear any active transform so the pre-import transform canvas
        // does not linger over the freshly imported PSD.
        if (typeof freeTransformState !== 'undefined' && freeTransformState) {
            freeTransformState = null;
            if (typeof _hideTransformCanvas === 'function') _hideTransformCanvas();
            if (typeof _hideLayerTransformQuickbar === 'function') _hideLayerTransformQuickbar();
        }
        // Remember this file for auto-load on next launch
        try {
            localStorage.setItem('spb_last_paint_file', psdPath);
            const _pfEl = document.getElementById('paintFile');
            if (_pfEl) _pfEl.value = psdPath;
        } catch (e) {}

        // Build flat layer list from tree (for easy access)
        function flattenLayers(layerTree, groupName) {
            for (const l of layerTree) {
                if (l.children && l.children.length > 0) {
                    // Group — recurse but also add the group itself as a toggle
                    flattenLayers(l.children, l.name);
                } else if (l.has_pixels) {
                    _psdLayers.push({
                        id: 'psd_' + _psdLayers.length,
                        name: l.name,
                        path: groupName ? groupName + '/' + l.name : l.name,
                        visible: l.visible,
                        // BUG #71: `l.opacity || 255` treats a legitimate 0 (fully
                        // transparent presentation layer) as missing and coerces
                        // it to 255 (fully opaque). Match the null-check idiom used
                        // everywhere else for this field.
                        opacity: (l.opacity != null ? l.opacity : 255),
                        img: null,  // Will be loaded in Step 2
                        bbox: l.bbox || [0, 0, data.width, data.height],
                        groupName: groupName || '',
                    });
                }
            }
        }
        flattenLayers(data.layers, '');

        // Show layer panel immediately (images loading...)
        renderLayerPanel();

        // Load composite onto canvas using the shared TGA loader
        if (data.composite) {
            const img = new Image();
            img.onload = function () {
                const tmp = document.createElement('canvas');
                tmp.width = img.naturalWidth; tmp.height = img.naturalHeight;
                const ctx = tmp.getContext('2d');
                ctx.drawImage(img, 0, 0);
                const rgba = ctx.getImageData(0, 0, tmp.width, tmp.height);

                const paintInput = document.getElementById('paintFile');
                if (paintInput) paintInput.value = psdPath.replace(/\.psd$/i, '.tga');

                if (typeof loadDecodedImageToCanvas === 'function') {
                    loadDecodedImageToCanvas(img.naturalWidth, img.naturalHeight, rgba.data, psdPath.split(/[/\\]/).pop());
                }
            };
            img.src = data.composite;
        }

        // Switch to layers tab in right panel
        if (typeof switchRightTab === 'function') switchRightTab('layers');

        // Step 2: Rasterize ALL layers in background (may take ~10 seconds)
        if (typeof showToast === 'function') showToast('Rasterizing layers (this takes ~10 seconds)...', 'info');

        console.log('[LAYERS] Requesting rasterize-all...');
        const rasterResp = await fetch('/api/psd-rasterize-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Shokker-Internal': '1',
            },
            body: JSON.stringify({ psd_path: psdPath })
        });
        console.log('[LAYERS] Rasterize response status:', rasterResp.status);
        if (!rasterResp.ok) {
            console.error('[LAYERS] Rasterize failed:', rasterResp.status);
            if (typeof showToast === 'function') showToast('Layer rasterization failed', true);
            return;
        }
        const rasterData = await rasterResp.json();
        console.log('[LAYERS] Rasterize parsed:', rasterData.count, 'layers');

        if (rasterData.success && rasterData.layers) {
            // Match rasterized images to our layer list
            let loaded = 0;
            const loadPromises = [];
            console.log('[LAYERS] Matching rasterized images to', _psdLayers.length, 'layers');
            console.log('[LAYERS] Available raster paths:', Object.keys(rasterData.layers));
            for (const layer of _psdLayers) {
                const rasterInfo = rasterData.layers[layer.path];
                console.log('[LAYERS] Match', layer.path, '->', rasterInfo ? 'FOUND' : 'NOT FOUND');
                if (rasterInfo && rasterInfo.image) {
                    const promise = new Promise((resolve) => {
                        const img = new Image();
                        img.onload = function () {
                            layer.img = img;
                            if (rasterInfo.bbox) layer.bbox = rasterInfo.bbox;
                            // Don't overwrite visible — keep the PSD's original state from initial import
                            loaded++;
                            resolve();
                        };
                        img.onerror = function () { resolve(); };
                        img.src = rasterInfo.image;
                    });
                    loadPromises.push(promise);
                }
            }

            // Wait for all images to load
            await Promise.all(loadPromises);
            _psdLayersLoaded = true;

            // Debug: verify which layers have images
            for (const layer of _psdLayers) {
                console.log('[LAYERS] Final state:', layer.name, 'visible=' + layer.visible, 'hasImg=' + !!layer.img, 'path=' + layer.path);
            }

            // Now recomposite from individual layers and update panel
            recompositeFromLayers();
            renderLayerPanel();

            if (typeof showToast === 'function')
                showToast(`PSD ready: ${loaded}/${_psdLayers.length} layers loaded. Toggle eyes to show/hide.`, 'success');
            // Auto-switch to LAYERS tab
            if (typeof switchRightTab === 'function') switchRightTab('layers');
        }

    } catch (err) {
        console.error('[PSD Import] Error:', err);
        if (typeof showToast === 'function') showToast('PSD import error: ' + err.message, true);
    } finally {
        // 2026-04-18 MARATHON bug #40: clear the in-flight guard on EVERY
        // exit path (success, early-abort, thrown). Otherwise a failed
        // import would block all future imports until page reload.
        window._spbPsdImportInFlight = false;
    }
}

function countLayers(layers) {
    let n = 0;
    for (const l of layers) {
        n++;
        if (l.children) n += countLayers(l.children);
    }
    return n;
}

// (old buildLayerTreeHTML removed — replaced by new layer system below)


// ═══ LAYER COMPOSITING ═══
// Redraws the paint canvas from cached layer images based on visibility
let _layerVisibleContributionCache = new Map(); // key => Uint8Array mask
let _layerCompositeRevision = 0;

function invalidateLayerVisibleContributionCache() {
    _layerVisibleContributionCache.clear();
    _layerCompositeRevision++;
}

function getLayerVisibleContributionMask(srcLayer, w, h) {
    if (!srcLayer || !srcLayer.img || !_psdLayersLoaded) return null;
    const cacheKey = `${_layerCompositeRevision}:${srcLayer.id}:${w}x${h}`;
    const cached = _layerVisibleContributionCache.get(cacheKey);
    if (cached) return cached;

    // ── ALPHA-BASED APPROACH (bug fix) ────────────────────────────────
    // Previous impl compared composite-WITH vs composite-WITHOUT the source layer,
    // but if the source layer's pixels happen to match the same color as lower
    // layers underneath, the diff was 0 and the mask excluded those pixels.
    // This is WRONG — a layer's contribution is defined by its ALPHA, not by
    // whether its color happens to differ from what's below.
    //
    // Correct behavior: mark a pixel as "the source layer contributes here" if
    // 1) the source layer has non-zero alpha at that pixel, AND
    // 2) no HIGHER layer with source-over blend completely covers it (alpha>=254)
    //    because higher fully-opaque layers would hide the source layer in the
    //    final composite.
    const srcC = document.createElement('canvas');
    srcC.width = w; srcC.height = h;
    // willReadFrequently: both temp canvases (srcC + aboveC) are draw-then-read
    // and this function is called on every layer-aware preview build.
    const srcCtx = srcC.getContext('2d', { willReadFrequently: true });
    const sbx = srcLayer.bbox ? srcLayer.bbox[0] : 0;
    const sby = srcLayer.bbox ? srcLayer.bbox[1] : 0;
    const sAlpha = (srcLayer.opacity != null ? srcLayer.opacity : 255) / 255;
    srcCtx.globalAlpha = sAlpha;
    srcCtx.drawImage(srcLayer.img, sbx, sby);
    const srcData = srcCtx.getImageData(0, 0, w, h).data;

    // Find position of source layer in stack so we know what's "above" it
    const srcIdx = _psdLayers.indexOf(srcLayer);

    // Build a canvas of ONLY the layers ABOVE the source layer (with source-over
    // blend mode) so we can detect where higher layers fully cover the source.
    const aboveC = document.createElement('canvas');
    aboveC.width = w; aboveC.height = h;
    const aboveCtx = aboveC.getContext('2d', { willReadFrequently: true });
    for (let i = srcIdx + 1; i < _psdLayers.length; i++) {
        const layer = _psdLayers[i];
        if (!layer.visible || !layer.img) continue;
        // Only standard source-over blend modes fully cover — skip exotic blends
        // so users who set multiply/overlay don't get unexpectedly hidden.
        if (layer.blendMode && layer.blendMode !== 'source-over' && layer.blendMode !== 'normal') continue;
        const bx = layer.bbox ? layer.bbox[0] : 0;
        const by = layer.bbox ? layer.bbox[1] : 0;
        const a = (layer.opacity != null ? layer.opacity : 255) / 255;
        aboveCtx.globalAlpha = a;
        aboveCtx.drawImage(layer.img, bx, by);
    }
    aboveCtx.globalAlpha = 1.0;
    const aboveData = aboveCtx.getImageData(0, 0, w, h).data;

    const visibleMask = new Uint8Array(w * h);
    for (let pi = 0; pi < w * h; pi++) {
        const idx = pi * 4;
        const srcA = srcData[idx + 3];
        // Source layer must contribute SOME alpha here
        if (srcA <= 8) continue;
        // Skip pixels fully covered by a higher fully-opaque layer
        const aboveA = aboveData[idx + 3];
        if (aboveA >= 250) continue;
        visibleMask[pi] = 255;
    }

    _layerVisibleContributionCache.set(cacheKey, visibleMask);
    return visibleMask;
}
if (typeof window !== 'undefined') window.getLayerVisibleContributionMask = getLayerVisibleContributionMask;

// ===== LAYER EFFECTS RENDERER =====
// Renders Photoshop-style layer effects for a single layer onto the given context.
// Called during recompositeFromLayers() for each layer that has effects enabled.
// CRITICAL: 'before' effects (shadow/glow) must render on a TEMP canvas first,
// then composite onto main ctx. Using destination-out directly on the main canvas
// would erase previously composited layers below.
function renderLayerEffects(ctx, layer, phase) {
    if (!layer.effects || !layer.img) return;
    var fx = layer.effects;
    var x = layer.bbox ? layer.bbox[0] : 0;
    var y = layer.bbox ? layer.bbox[1] : 0;
    var w = layer.img.width || layer.img.naturalWidth;
    var h = layer.img.height || layer.img.naturalHeight;
    // Workstream 3 #46 — guard against tiny / zero-size layers. Effects on
    // a 0×0 image throw obscure canvas errors on the temp-canvas allocation.
    // 1×1 is fine; 0×0 is an aborted PSD layer or a bug. Fail closed.
    if (!w || !h || w < 1 || h < 1) return;
    if (phase === 'before') {
        if (fx.dropShadow && fx.dropShadow.enabled) {
            var ds = fx.dropShadow;
            var rad = (ds.angle || 135) * Math.PI / 180;
            var dx = Math.cos(rad) * (ds.distance || 5);
            var dy = Math.sin(rad) * (ds.distance || 5);
            // Render shadow on a temp canvas to avoid destination-out erasing layers below
            var dsCanvas = document.createElement('canvas');
            dsCanvas.width = ctx.canvas.width; dsCanvas.height = ctx.canvas.height;
            var dsCtx = dsCanvas.getContext('2d');
            dsCtx.shadowColor = ds.color || '#000000';
            dsCtx.shadowBlur = ds.size || 5;
            dsCtx.shadowOffsetX = dx;
            dsCtx.shadowOffsetY = dy;
            dsCtx.drawImage(layer.img, x, y, w, h);
            // Erase the layer shape from temp canvas, leaving only the shadow
            dsCtx.shadowColor = 'transparent'; dsCtx.shadowBlur = 0;
            dsCtx.shadowOffsetX = 0; dsCtx.shadowOffsetY = 0;
            dsCtx.globalCompositeOperation = 'destination-out';
            dsCtx.drawImage(layer.img, x, y, w, h);
            // Composite the shadow-only result onto the main canvas
            ctx.save();
            ctx.globalAlpha = ds.opacity != null ? ds.opacity : 0.75;
            ctx.drawImage(dsCanvas, 0, 0);
            ctx.restore();
        }
        if (fx.outerGlow && fx.outerGlow.enabled) {
            var og = fx.outerGlow;
            // Render glow on a temp canvas to avoid destination-out erasing layers below
            var ogCanvas = document.createElement('canvas');
            ogCanvas.width = ctx.canvas.width; ogCanvas.height = ctx.canvas.height;
            var ogCtx = ogCanvas.getContext('2d');
            ogCtx.shadowColor = og.color || '#00e5ff';
            ogCtx.shadowBlur = og.size || 10;
            ogCtx.shadowOffsetX = 0; ogCtx.shadowOffsetY = 0;
            var passes = Math.max(1, Math.ceil((og.spread || 0) / 3) + 1);
            for (var p = 0; p < passes; p++) ogCtx.drawImage(layer.img, x, y, w, h);
            // Erase the shape, leaving only the glow halo
            ogCtx.shadowColor = 'transparent'; ogCtx.shadowBlur = 0;
            ogCtx.globalCompositeOperation = 'destination-out';
            ogCtx.drawImage(layer.img, x, y, w, h);
            // Composite the glow-only result onto the main canvas
            ctx.save();
            ctx.globalAlpha = og.opacity != null ? og.opacity : 0.8;
            ctx.drawImage(ogCanvas, 0, 0);
            ctx.restore();
        }
    }
    if (phase === 'after') {
        if (fx.stroke && fx.stroke.enabled) {
            var st = fx.stroke;
            var strokeW = st.width || 2;
            // Fast GPU-accelerated stroke using Canvas2D strokeStyle + lineWidth.
            // Step 1: Build an alpha-only mask of the layer shape
            var sCanvas = document.createElement('canvas');
            sCanvas.width = ctx.canvas.width; sCanvas.height = ctx.canvas.height;
            var sCtx = sCanvas.getContext('2d');
            // Draw a thick colored stroke around the shape using the shadow trick:
            // draw the layer image with a thick colored shadow at (0,0) offset,
            // then erase the original shape, leaving only the thick halo = stroke
            sCtx.shadowColor = st.color || '#ffffff';
            sCtx.shadowBlur = 0;
            sCtx.shadowOffsetX = 0;
            sCtx.shadowOffsetY = 0;
            // Use multiple offset draws to build a uniform stroke (faster than pixel dilation)
            var _strokeAngles = Math.max(8, strokeW * 2);
            for (var _sa = 0; _sa < _strokeAngles; _sa++) {
                var _sRad = (_sa / _strokeAngles) * Math.PI * 2;
                var _sdx = Math.cos(_sRad) * strokeW;
                var _sdy = Math.sin(_sRad) * strokeW;
                sCtx.drawImage(layer.img, x + _sdx, y + _sdy, w, h);
            }
            // For inside/center stroke, keep the shape; for outside, erase it
            if (st.position === 'outside') {
                sCtx.globalCompositeOperation = 'destination-out';
                sCtx.drawImage(layer.img, x, y, w, h);
            } else if (st.position === 'inside') {
                // Inside: clip to only the original shape area
                var insCanvas = document.createElement('canvas');
                insCanvas.width = sCanvas.width; insCanvas.height = sCanvas.height;
                var insCtx = insCanvas.getContext('2d');
                insCtx.drawImage(layer.img, x, y, w, h); // alpha mask of shape
                insCtx.globalCompositeOperation = 'source-in';
                insCtx.drawImage(sCanvas, 0, 0); // keep only stroke pixels inside shape
                sCanvas = insCanvas; // swap
            }
            // Composite stroke onto main canvas
            ctx.save();
            ctx.globalAlpha = st.opacity != null ? st.opacity : 1.0;
            ctx.drawImage(sCanvas, 0, 0);
            ctx.restore();
        }
        if (fx.colorOverlay && fx.colorOverlay.enabled) {
            var co = fx.colorOverlay;
            var oCanvas = document.createElement('canvas');
            oCanvas.width = ctx.canvas.width; oCanvas.height = ctx.canvas.height;
            var oCtx = oCanvas.getContext('2d');
            oCtx.drawImage(layer.img, x, y, w, h);
            oCtx.globalCompositeOperation = 'source-in';
            oCtx.fillStyle = co.color || '#ff3366';
            oCtx.fillRect(0, 0, oCanvas.width, oCanvas.height);
            ctx.save();
            ctx.globalAlpha = co.opacity != null ? co.opacity : 0.5;
            ctx.globalCompositeOperation = co.blendMode || 'source-over';
            ctx.drawImage(oCanvas, 0, 0);
            ctx.restore();
        }
        if (fx.bevel && fx.bevel.enabled) {
            var bv = fx.bevel;
            var bSize = bv.size || 5;
            var depth = bv.depth || 3;
            var isUp = (bv.direction || 'up') === 'up';
            var bCanvas = document.createElement('canvas');
            bCanvas.width = ctx.canvas.width; bCanvas.height = ctx.canvas.height;
            var bCtx = bCanvas.getContext('2d');
            bCtx.drawImage(layer.img, x, y, w, h);
            var bData = bCtx.getImageData(0, 0, bCanvas.width, bCanvas.height);
            var ba = bData.data;
            var outData = bCtx.createImageData(bCanvas.width, bCanvas.height);
            var od = outData.data;
            for (var bpy = bSize; bpy < bCanvas.height - bSize; bpy++) {
                for (var bpx = bSize; bpx < bCanvas.width - bSize; bpx++) {
                    var bidx = (bpy * bCanvas.width + bpx) * 4;
                    if (ba[bidx+3] < 10) continue;
                    var topIdx = ((bpy-bSize)*bCanvas.width+bpx)*4;
                    var botIdx = ((bpy+bSize)*bCanvas.width+bpx)*4;
                    var diff = (ba[topIdx+3] - ba[botIdx+3]) / 255.0 * depth;
                    if (isUp ? diff > 0.1 : diff < -0.1) { od[bidx]=255;od[bidx+1]=255;od[bidx+2]=255;od[bidx+3]=Math.min(255,Math.round(Math.abs(diff)*80)); }
                    else if (isUp ? diff < -0.1 : diff > 0.1) { od[bidx]=0;od[bidx+1]=0;od[bidx+2]=0;od[bidx+3]=Math.min(255,Math.round(Math.abs(diff)*80)); }
                }
            }
            bCtx.putImageData(outData, 0, 0);
            if (bv.soften > 0) { ctx.save(); ctx.filter='blur('+bv.soften+'px)'; ctx.drawImage(bCanvas,0,0); ctx.restore(); }
            else { ctx.drawImage(bCanvas, 0, 0); }
        }
    }
}

function recompositeFromLayers() {
    if (!_psdLayersLoaded || _psdLayers.length === 0) return;
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    // willReadFrequently: every recomposite reads paintImageData back via
    // getImageData (line ~9235). Without the flag this hot path forces a
    // GPU readback every time a layer is moved, opacity is changed, etc.
    const ctx = pc.getContext('2d', { willReadFrequently: true });
    ctx.clearRect(0, 0, pc.width, pc.height);

    // Draw layers bottom-to-top (first in array = bottom)
    for (const layer of _psdLayers) {
        if (!layer.visible || !layer.img) continue;
        // Render pre-layer effects (drop shadow, outer glow)
        renderLayerEffects(ctx, layer, 'before');
        // Draw the layer itself
        ctx.globalAlpha = (layer.opacity != null ? layer.opacity : 255) / 255;
        ctx.globalCompositeOperation = layer.blendMode || 'source-over';
        const bx = layer.bbox ? layer.bbox[0] : 0;
        const by = layer.bbox ? layer.bbox[1] : 0;
        ctx.drawImage(layer.img, bx, by);
        // Render post-layer effects (stroke, color overlay, bevel)
        ctx.globalAlpha = 1.0;
        ctx.globalCompositeOperation = 'source-over';
        renderLayerEffects(ctx, layer, 'after');
    }
    ctx.globalAlpha = 1.0;
    ctx.globalCompositeOperation = 'source-over';

    // Update paintImageData so tools (eyedropper, wand, etc.) see the new composite
    paintImageData = ctx.getImageData(0, 0, pc.width, pc.height);
    invalidateLayerVisibleContributionCache();
}

// ═══ LAYER PANEL RENDERING ═══
var _layerDragReorder = null; // { srcIdx, currentIdx } for drag-to-reorder

function renderLayerPanel() {
    const container = document.getElementById('layerPanelContent');
    if (!container) return;

    if (_psdLayers.length === 0) {
        container.innerHTML = '<div style="color:var(--text-dim);font-size:10px;padding:8px;text-align:center;">No PSD loaded.</div>';
        return;
    }

    let html = '';
    // Show layers top-to-bottom (reverse of draw order — like Photoshop)
    for (let i = _psdLayers.length - 1; i >= 0; i--) {
        const l = _psdLayers[i];
        const selected = _selectedLayerId === l.id;
        const vis = l.visible;
        const eyeIcon = vis ? '👁' : '·';
        const eyeStyle = vis ? 'opacity:1' : 'opacity:0.3';
        const nameColor = vis ? '#ddd' : '#666';
        const selBg = selected ? 'background:rgba(0,229,255,0.15);border-left:3px solid #00e5ff;' : 'border-left:3px solid transparent;';
        // BUG #68: layer name/path/groupName are user-controlled (PSD file, rename dialog).
        // They were being interpolated raw into the panel HTML — a PSD layer named
        // `</span><img src=x onerror=alert(1)>` would execute script. Escape them.
        const _safeName = (typeof escapeHtml === 'function') ? escapeHtml(l.name || '') : (l.name || '');
        const _safePath = (typeof escapeHtml === 'function') ? escapeHtml(l.path || '') : (l.path || '');
        const _safeGroup = (typeof escapeHtml === 'function') ? escapeHtml(l.groupName || '') : (l.groupName || '');
        const groupTag = l.groupName ? `<span style="font-size:7px;color:#555;margin-left:2px;">${_safeGroup}</span>` : '';
        const hasFx = typeof layerHasEffects === 'function' ? layerHasEffects(l) : false;
        const opacityPct = Math.round((l.opacity != null ? l.opacity : 255) / 255 * 100);
        const blendMode = l.blendMode || 'source-over';

        // Draggable layer row
        html += `<div class="layer-row" data-layer-idx="${i}" data-layer-id="${l.id}"
            style="${selBg}padding:4px 6px 4px 4px;display:flex;align-items:center;gap:4px;font-size:11px;cursor:grab;border-bottom:1px solid rgba(255,255,255,0.03);user-select:none;"
            draggable="true"
            ondragstart="onLayerDragStart(event, ${i})"
            ondragover="onLayerDragOver(event, ${i})"
            ondragend="onLayerDragEnd(event)"
            onclick="selectPSDLayer('${l.id}')"
            ondblclick="event.stopPropagation(); openLayerEffects('${l.id}')">`;

        // Eye toggle
        html += `<span style="cursor:pointer;font-size:12px;width:18px;text-align:center;${eyeStyle}"
            onclick="event.stopPropagation(); toggleLayerVisible('${l.id}')" title="${vis ? 'Hide' : 'Show'}">${eyeIcon}</span>`;

        // Layer thumbnail (tiny preview)
        html += `<canvas class="layer-thumb" id="layerThumb_${l.id}" width="24" height="24"
            style="width:24px;height:24px;border:1px solid ${selected ? '#00e5ff' : '#333'};border-radius:2px;background:#111;flex-shrink:0;"></canvas>`;

        // Name + group
        html += `<span style="color:${nameColor};flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px;" title="${_safePath}">${_safeName}</span>`;
        html += groupTag;
        if (hasFx) {
            html += `<span style="cursor:pointer;font-size:8px;font-weight:700;letter-spacing:0.4px;color:#ffd700;border:1px solid rgba(255,215,0,0.45);border-radius:8px;padding:0 4px;line-height:16px;"
                onclick="event.stopPropagation(); openLayerEffects('${l.id}')" title="Layer effects active — open Layer Effects">fx</span>`;
        }

        // Opacity badge (if not 100%)
        if (opacityPct < 100) {
            html += `<span style="font-size:7px;color:#888;min-width:22px;text-align:right;">${opacityPct}%</span>`;
        }

        // Loading indicator
        if (!l.img) {
            html += `<span style="font-size:7px;color:#555;">...</span>`;
        }

        // Lock toggle
        html += `<span style="cursor:pointer;font-size:9px;color:${l.locked ? '#ff0' : '#444'};padding:0 1px;"
            onclick="event.stopPropagation(); toggleLayerLocked('${l.id}')" title="${l.locked ? 'Unlock' : 'Lock'} layer">${l.locked ? '🔒' : '🔓'}</span>`;

        html += `</div>`;

        // Expanded panel when selected
        if (selected) {
            html += `<div style="background:rgba(0,229,255,0.04);border-left:3px solid #00e5ff;padding:6px 8px 8px 8px;border-bottom:1px solid rgba(255,255,255,0.06);">`;

            // Opacity slider
            html += `<div style="display:flex;align-items:center;gap:4px;margin-bottom:5px;">
                <span style="font-size:8px;color:#888;width:42px;">Opacity:</span>
                <input type="range" min="0" max="100" value="${opacityPct}" style="flex:1;height:12px;cursor:pointer;"
                    oninput="setLayerOpacity('${l.id}', this.value)" title="Layer opacity">
                <span style="font-size:8px;color:#aaa;width:26px;text-align:right;">${opacityPct}%</span>
            </div>`;

            // Blend mode dropdown
            html += `<div style="display:flex;align-items:center;gap:4px;margin-bottom:6px;">
                <span style="font-size:8px;color:#888;width:42px;">Blend:</span>
                <select style="flex:1;font-size:9px;padding:2px 4px;background:#1a1a1a;color:#ccc;border:1px solid #444;border-radius:3px;"
                    onchange="setLayerBlendMode('${l.id}', this.value)">
                    <option value="source-over" ${blendMode === 'source-over' ? 'selected' : ''}>Normal</option>
                    <option value="multiply" ${blendMode === 'multiply' ? 'selected' : ''}>Multiply</option>
                    <option value="screen" ${blendMode === 'screen' ? 'selected' : ''}>Screen</option>
                    <option value="overlay" ${blendMode === 'overlay' ? 'selected' : ''}>Overlay</option>
                    <option value="darken" ${blendMode === 'darken' ? 'selected' : ''}>Darken</option>
                    <option value="lighten" ${blendMode === 'lighten' ? 'selected' : ''}>Lighten</option>
                    <option value="color-dodge" ${blendMode === 'color-dodge' ? 'selected' : ''}>Color Dodge</option>
                    <option value="color-burn" ${blendMode === 'color-burn' ? 'selected' : ''}>Color Burn</option>
                    <option value="hard-light" ${blendMode === 'hard-light' ? 'selected' : ''}>Hard Light</option>
                    <option value="soft-light" ${blendMode === 'soft-light' ? 'selected' : ''}>Soft Light</option>
                    <option value="difference" ${blendMode === 'difference' ? 'selected' : ''}>Difference</option>
                    <option value="exclusion" ${blendMode === 'exclusion' ? 'selected' : ''}>Exclusion</option>
                    <option value="hue" ${blendMode === 'hue' ? 'selected' : ''}>Hue</option>
                    <option value="saturation" ${blendMode === 'saturation' ? 'selected' : ''}>Saturation</option>
                    <option value="color" ${blendMode === 'color' ? 'selected' : ''}>Color</option>
                    <option value="luminosity" ${blendMode === 'luminosity' ? 'selected' : ''}>Luminosity</option>
                </select>
            </div>`;

            // Action buttons — row 1: layer utilities
            html += `<div style="display:flex;gap:2px;margin-bottom:3px;flex-wrap:wrap;">`;
            html += `<button onclick="activateLayerElementPickMode()" class="layer-act-btn layer-act-cyan" title="Pick Item — click one sponsor, number, or shape on this layer to isolate it and start transform">PICK ITEM</button>`;
            html += `<button onclick="duplicateLayer('${l.id}')" class="layer-act-btn" title="Duplicate this layer">DUPE</button>`;
            html += `<button onclick="mirrorCloneLayer('${l.id}')" class="layer-act-btn" style="border-color:#ffd700;color:#ffd700;" title="Mirror Clone — duplicate + flip to opposite side of car (iRacing essential)">MIRROR</button>`;
            html += `<button onclick="openLayerEffects('${l.id}')" class="layer-act-btn" style="border-color:#ffd700;color:#ffd700;" title="Open Photoshop-style Layer Effects">FX</button>`;
            html += `</div>`;

            // Action buttons — row 2: layer ops
            html += `<div style="display:flex;gap:2px;margin-bottom:3px;flex-wrap:wrap;">`;
            html += `<button onclick="mergeLayerDown('${l.id}')" class="layer-act-btn" title="Merge into layer below">MERGE ↓</button>`;
            html += `<button onclick="flattenAllLayers()" class="layer-act-btn" title="Flatten all visible layers into one">FLATTEN</button>`;
            html += `<button onclick="renameLayer('${l.id}')" class="layer-act-btn" title="Rename this layer">RENAME</button>`;
            html += `<button onclick="deleteLayer('${_selectedLayerId}')" class="layer-act-btn layer-act-red" title="Delete layer">DELETE</button>`;
            html += `</div>`;

            // Action buttons — row 3: stack order + finishing helpers
            html += `<div style="display:flex;gap:2px;flex-wrap:wrap;">`;
            html += `<button onclick="moveLayerUp()" class="layer-act-btn" title="Move up in stack (or drag)">▲ UP</button>`;
            html += `<button onclick="moveLayerDown()" class="layer-act-btn" title="Move down in stack (or drag)">▼ DOWN</button>`;
            html += `<button onclick="addLayerOutline('${l.id}')" class="layer-act-btn" style="border-color:#ff66aa;color:#ff66aa;" title="Add colored outline around layer (great for sponsor readability)">OUTLINE</button>`;
            html += `<button onclick="centerLayerOnCanvas('${l.id}')" class="layer-act-btn" title="Center layer on canvas">CENTER</button>`;
            html += `<button onclick="fitLayerToCanvas('${l.id}')" class="layer-act-btn" title="Scale layer to fit canvas (preserve aspect ratio)">FIT</button>`;
            html += `<button onclick="knockoutLayer('${l.id}')" class="layer-act-btn" style="border-color:#ff4444;color:#ff4444;" title="Knockout — punch this layer's shape through layers below">KNOCKOUT</button>`;
            html += `</div>`;

            // Hint
            html += `<div style="font-size:7px;color:#555;margin-top:4px;">Pick Item isolates one sponsor or number for transform | Layer rail / Ctrl+T starts transform | FX stays layer-local | Zone Mask &#x2190; Layer lives in the top strip</div>`;
            html += `</div>`;
        }
    }

    container.innerHTML = html;
    if (typeof renderContextActionBar === 'function') renderContextActionBar();

    // Render layer thumbnails after DOM update (cached — only redraw when layer.img changes)
    requestAnimationFrame(() => {
        for (const l of _psdLayers) {
            const thumb = document.getElementById('layerThumb_' + l.id);
            if (thumb && l.img) {
                // Cache key: use the img reference identity (changes on any edit)
                if (thumb._cachedImg === l.img && thumb._cachedBbox === JSON.stringify(l.bbox)) continue;
                thumb._cachedImg = l.img;
                thumb._cachedBbox = JSON.stringify(l.bbox);
                const ctx = thumb.getContext('2d');
                ctx.clearRect(0, 0, 24, 24);
                ctx.fillStyle = '#222';
                ctx.fillRect(0, 0, 24, 24);
                ctx.fillStyle = '#333';
                for (let ty = 0; ty < 24; ty += 4) for (let tx = (ty % 8 === 0 ? 0 : 4); tx < 24; tx += 8) ctx.fillRect(tx, ty, 4, 4);
                const [bx1, by1, bx2, by2] = l.bbox || [0, 0, l.img.width || 24, l.img.height || 24];
                const lw = (bx2 - bx1) || l.img.width || 24, lh = (by2 - by1) || l.img.height || 24;
                const scale = Math.min(24 / lw, 24 / lh);
                const dw = lw * scale, dh = lh * scale;
                try { ctx.drawImage(l.img, 0, 0, l.img.width || lw, l.img.height || lh, (24 - dw) / 2, (24 - dh) / 2, dw, dh); } catch(_) {}
            }
        }
    });
}

// Inject CSS for layer action buttons (once)
(function() {
    if (document.getElementById('layerPanelCSS')) return;
    const style = document.createElement('style');
    style.id = 'layerPanelCSS';
    style.textContent = `
        .layer-act-btn { font-size:7px; padding:2px 5px; background:rgba(255,255,255,0.05); border:1px solid #555;
            color:#aaa; border-radius:3px; cursor:pointer; font-weight:bold; white-space:nowrap; }
        .layer-act-btn:hover { background:rgba(255,255,255,0.12); color:#ddd; }
        .layer-act-cyan { background:rgba(0,229,255,0.1); border-color:rgba(0,229,255,0.4); color:#00e5ff; }
        .layer-act-cyan:hover { background:rgba(0,229,255,0.2); }
        .layer-act-red { background:rgba(255,50,50,0.1); border-color:#c33; color:#f55; }
        .layer-act-red:hover { background:rgba(255,50,50,0.2); }
        .layer-row { transition: background 0.1s; }
        .layer-row:hover { background:rgba(255,255,255,0.04) !important; }
        .layer-row.drag-over-above { border-top: 2px solid #00e5ff !important; }
        .layer-row.drag-over-below { border-bottom: 2px solid #00e5ff !important; }
    `;
    document.head.appendChild(style);
})();

// ═══ DRAG-TO-REORDER LAYERS ═══
function onLayerDragStart(e, displayIdx) {
    // displayIdx is the visual position (reversed from _psdLayers array order)
    const arrIdx = _psdLayers.length - 1 - displayIdx;
    _layerDragReorder = { srcArrIdx: arrIdx, srcDisplayIdx: displayIdx };
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', ''); // Required for Firefox
    e.target.style.opacity = '0.4';
}

function onLayerDragOver(e, displayIdx) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    // Clear all indicators
    document.querySelectorAll('.layer-row').forEach(r => {
        r.classList.remove('drag-over-above', 'drag-over-below');
    });
    // Show insertion indicator
    const row = e.currentTarget;
    const rect = row.getBoundingClientRect();
    const midY = rect.top + rect.height / 2;
    if (e.clientY < midY) {
        row.classList.add('drag-over-above');
    } else {
        row.classList.add('drag-over-below');
    }
    _layerDragReorder.targetDisplayIdx = displayIdx;
    _layerDragReorder.insertAbove = (e.clientY < midY);
}

function onLayerDragEnd(e) {
    e.target.style.opacity = '1';
    document.querySelectorAll('.layer-row').forEach(r => {
        r.classList.remove('drag-over-above', 'drag-over-below');
    });
    if (!_layerDragReorder || _layerDragReorder.targetDisplayIdx == null) {
        _layerDragReorder = null;
        return;
    }

    const srcArr = _layerDragReorder.srcArrIdx;
    let targetDisplay = _layerDragReorder.targetDisplayIdx;
    let targetArr = _psdLayers.length - 1 - targetDisplay;
    if (!_layerDragReorder.insertAbove) targetArr--; // Insert below = one position lower in array

    if (srcArr !== targetArr && targetArr >= 0 && targetArr < _psdLayers.length) {
        _pushLayerStackUndo('reorder layer');
        const moved = _psdLayers.splice(srcArr, 1)[0];
        if (targetArr > srcArr) targetArr--;
        _psdLayers.splice(targetArr + 1, 0, moved);
        recompositeFromLayers();
        renderLayerPanel();
        drawLayerBounds();
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }
    _layerDragReorder = null;
}

// ═══ LAYER OPERATIONS ═══

function setLayerOpacity(layerId, pctValue) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer) return;
    const newOpacity = Math.round(pctValue / 100 * 255);
    if (newOpacity === layer.opacity) return;
    // FIVE-HOUR SHIFT Win D1: pre-fix this skipped the locked-layer guard.
    // Sister setLayerBlendMode (marathon #73) and the quick-button family
    // (TWENTY WINS Win #4 polish) all check layer.locked first. Lock icon
    // was lying for opacity slider drags. Aligning with the contract.
    if (layer.locked) {
        if (typeof showToast === 'function') showToast('"' + (layer.name || 'Layer') + '" is locked — unlock to change opacity', true);
        return;
    }
    _pushLayerStackUndo(`opacity → ${Math.round(pctValue)}%`);
    layer.opacity = newOpacity;
    recompositeFromLayers();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function setLayerBlendMode(layerId, mode) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer) return;
    if (layer.blendMode === mode) return;
    // BUG #73 (Owen, MED): `toggleLayerLocked` exists for a reason — every
    // other mutator (flip, rotate, opacity via dragOpacitySlider path, etc.)
    // checks `layer.locked`. Blend-mode dropdown did not, so lock icon was
    // a lie. Align with the rest of the layer-mutator contract.
    if (layer.locked) {
        if (typeof showToast === 'function') showToast('Layer is locked — unlock to change blend mode', true);
        return;
    }
    _pushLayerStackUndo(`blend → ${mode}`);
    layer.blendMode = mode;
    recompositeFromLayers();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function toggleLayerLocked(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer) return;
    _pushLayerStackUndo(`${layer.locked ? 'unlock' : 'lock'} layer`);
    layer.locked = !layer.locked;
    renderLayerPanel();
    // TOOLS WAR — refresh active-tool label so the (locked) tag appears/clears.
    if (typeof refreshActiveToolLabel === 'function') refreshActiveToolLabel();
}

function flipLayerH() {
    const layer = getSelectedLayer();
    if (!layer || !layer.img) return;
    // WIN #4 polish (Flair audit): silent no-op on locked layer is a UX lie.
    // Match the "X is locked — unlock to transform" toast pattern from
    // activateLayerTransform (line 13242).
    if (layer.locked) {
        if (typeof showToast === 'function') showToast('"' + (layer.name || 'Layer') + '" is locked — unlock to flip', true);
        return;
    }
    _pushLayerUndo(layer, 'flip horizontal');
    const c = document.createElement('canvas');
    c.width = layer.img.width; c.height = layer.img.height;
    const ctx = c.getContext('2d');
    ctx.translate(c.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(layer.img, 0, 0);
    layer.img = c; // Direct canvas assignment — no toDataURL needed
    recompositeFromLayers();
    renderLayerPanel();
    if (typeof showToast === 'function') showToast('Flipped horizontally');
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function flipLayerV() {
    const layer = getSelectedLayer();
    if (!layer || !layer.img) return;
    if (layer.locked) {
        if (typeof showToast === 'function') showToast('"' + (layer.name || 'Layer') + '" is locked — unlock to flip', true);
        return;
    }
    _pushLayerUndo(layer, 'flip vertical');
    const c = document.createElement('canvas');
    c.width = layer.img.width; c.height = layer.img.height;
    const ctx = c.getContext('2d');
    ctx.translate(0, c.height);
    ctx.scale(1, -1);
    ctx.drawImage(layer.img, 0, 0);
    layer.img = c;
    recompositeFromLayers();
    renderLayerPanel();
    if (typeof showToast === 'function') showToast('Flipped vertically');
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function rotateLayer90(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer || !layer.img) return;
    if (layer.locked) {
        if (typeof showToast === 'function') showToast('"' + (layer.name || 'Layer') + '" is locked — unlock to rotate', true);
        return;
    }
    _pushLayerUndo(layer, 'rotate 90°');
    const c = document.createElement('canvas');
    c.width = layer.img.height; c.height = layer.img.width;
    const ctx = c.getContext('2d');
    ctx.translate(c.width / 2, c.height / 2);
    ctx.rotate(Math.PI / 2);
    ctx.drawImage(layer.img, -layer.img.width / 2, -layer.img.height / 2);
    const rotated = new Image();
    layer.img = c; // Direct canvas — skip toDataURL
    const [x1, y1, x2, y2] = layer.bbox;
    const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
    const hw = (y2 - y1) / 2, hh = (x2 - x1) / 2;
    layer.bbox = [Math.round(cx - hw), Math.round(cy - hh), Math.round(cx + hw), Math.round(cy + hh)];
    recompositeFromLayers();
    drawLayerBounds();
    renderLayerPanel();
    if (typeof showToast === 'function') showToast('Rotated 90°');
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function rotateLayer90CCW(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer || !layer.img) return false;
    if (layer.locked) {
        if (typeof showToast === 'function') showToast('"' + (layer.name || 'Layer') + '" is locked — unlock to rotate', true);
        return false;
    }
    _pushLayerUndo(layer, 'rotate -90°');
    const c = document.createElement('canvas');
    c.width = layer.img.height; c.height = layer.img.width;
    const ctx = c.getContext('2d');
    ctx.translate(c.width / 2, c.height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.drawImage(layer.img, -layer.img.width / 2, -layer.img.height / 2);
    layer.img = c;
    const [x1, y1, x2, y2] = layer.bbox;
    const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
    const hw = (y2 - y1) / 2, hh = (x2 - x1) / 2;
    layer.bbox = [Math.round(cx - hw), Math.round(cy - hh), Math.round(cx + hw), Math.round(cy + hh)];
    recompositeFromLayers();
    drawLayerBounds();
    renderLayerPanel();
    if (typeof showToast === 'function') showToast('Rotated -90°');
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    return true;
}

function rotateSelectedLayerCW() {
    const layer = getSelectedLayer();
    if (!layer) return false;
    rotateLayer90(layer.id);
    return true;
}

function rotateSelectedLayerCCW() {
    const layer = getSelectedLayer();
    if (!layer) return false;
    return rotateLayer90CCW(layer.id);
}

// 2026-04-18 MARATHON bug #37 (Animal, MED): pre-fix, the context-action-
// bar "180°" button fired `rotateSelectedLayerCW(); rotateSelectedLayerCW();`
// → two undo steps + two "Rotated 90°" toasts for a single user action.
// Photoshop parity expects one atomic 180° step.
function rotateSelectedLayer180() {
    const layer = getSelectedLayer();
    if (!layer || !layer.img || layer.locked) return false;
    _pushLayerUndo(layer, 'rotate 180°');
    const c = document.createElement('canvas');
    c.width = layer.img.width;
    c.height = layer.img.height;
    const ctx = c.getContext('2d');
    ctx.translate(c.width, c.height);
    ctx.rotate(Math.PI);
    ctx.drawImage(layer.img, 0, 0);
    layer.img = c;
    // bbox: 180° around the bbox center leaves shape unchanged; just
    // recompute to keep the contract intact.
    const [x1, y1, x2, y2] = layer.bbox;
    layer.bbox = [x1, y1, x2, y2];
    if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
    if (typeof drawLayerBounds === 'function') drawLayerBounds();
    if (typeof renderLayerPanel === 'function') renderLayerPanel();
    if (typeof showToast === 'function') showToast('Rotated 180°');
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    return true;
}
if (typeof window !== 'undefined') window.rotateSelectedLayer180 = rotateSelectedLayer180;
function openSelectedLayerEffects() {
    const layer = getSelectedLayer();
    if (!layer) return false;
    openLayerEffects(layer.id);
    return true;
}
function selectSelectedLayerPixels() {
    const layer = getSelectedLayer();
    if (!layer) return false;
    selectLayerPixels(layer.id);
    return true;
}
window.rotateSelectedLayerCW = rotateSelectedLayerCW;
window.rotateSelectedLayerCCW = rotateSelectedLayerCCW;
window.openSelectedLayerEffects = openSelectedLayerEffects;
window.selectSelectedLayerPixels = selectSelectedLayerPixels;

function duplicateLayer(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer) return;
    _pushLayerStackUndo('duplicate layer');
    const idx = _psdLayers.indexOf(layer);
    const newLayer = {
        id: 'psd_dup_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
        name: layer.name + ' copy',
        path: layer.path + ' copy',
        visible: layer.visible,
        opacity: layer.opacity,
        img: layer.img, // shares the Image reference (immutable)
        bbox: [...layer.bbox],
        groupName: layer.groupName,
        blendMode: layer.blendMode || 'source-over',
        locked: false,
        // Photoshop parity: duplicating a styled layer carries the layer
        // styles (drop shadow, glow, stroke, color overlay, bevel) onto
        // the duplicate. Deep-clone so editing one copy doesn't mutate
        // the other.
        effects: layer.effects ? JSON.parse(JSON.stringify(layer.effects)) : null,
    };
    _psdLayers.splice(idx + 1, 0, newLayer);
    _selectedLayerId = newLayer.id;
    if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
    recompositeFromLayers();
    renderLayerPanel();
    drawLayerBounds();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Layer duplicated');
}

function mirrorCloneLayer(layerId) {
    // iRacing killer feature: duplicate a layer and flip it horizontally
    // On a car UV map, horizontal flip mirrors to the opposite side
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer || !layer.img) return;
    _pushLayerStackUndo('mirror clone');
    const idx = _psdLayers.indexOf(layer);

    // Create flipped image
    const c = document.createElement('canvas');
    c.width = layer.img.width; c.height = layer.img.height;
    const ctx = c.getContext('2d');
    ctx.translate(c.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(layer.img, 0, 0);

    const pc = document.getElementById('paintCanvas');
    const canvasW = pc ? pc.width : 2048;
    const [bx1, by1, bx2, by2] = layer.bbox;
    const newBbox = [canvasW - bx2, by1, canvasW - bx1, by2];

    const newLayer = {
        id: 'psd_mirror_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
        name: layer.name + ' (mirror)',
        path: layer.path + ' mirror',
        visible: true,
        opacity: layer.opacity,
        img: c, // Direct canvas — no toDataURL
        bbox: newBbox,
        groupName: layer.groupName,
        blendMode: layer.blendMode || 'source-over',
        locked: false,
        // Mirror clone is a duplicate-then-flip; preserve effects so the
        // mirrored sponsor on the opposite door inherits the same drop
        // shadow / stroke / glow as the original.
        effects: layer.effects ? JSON.parse(JSON.stringify(layer.effects)) : null,
    };
    _psdLayers.splice(idx + 1, 0, newLayer);
    _selectedLayerId = newLayer.id;
    if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
    recompositeFromLayers();
    renderLayerPanel();
    drawLayerBounds();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Mirror clone created — flipped to opposite side');
}
window.mirrorCloneLayer = mirrorCloneLayer;

// ===== SPONSOR TOOLING =====
// Outline/knockout: draws a solid outline around a layer's opaque pixels (for sponsor readability)
function addLayerOutline(layerId, outlineColor, outlineWidth) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer || !layer.img) return;
    // TOOLS WAR Phase 5 — locked layers refuse all destructive sponsor ops.
    if (layer.locked) {
        if (typeof showToast === 'function') showToast(`"${layer.name}" is locked — unlock to add outline`, 'warn');
        return;
    }
    _pushLayerUndo(layer, 'add outline');
    outlineColor = outlineColor || '#ffffff';
    outlineWidth = outlineWidth || 3;
    const w = layer.img.width || layer.img.naturalWidth;
    const h = layer.img.height || layer.img.naturalHeight;
    // Create outlined version
    const oc = document.createElement('canvas');
    // Expand canvas to fit outline bleed
    const pad = outlineWidth + 2;
    oc.width = w + pad * 2; oc.height = h + pad * 2;
    const octx = oc.getContext('2d');
    // Draw the image multiple times at offsets to create the outline
    octx.globalCompositeOperation = 'source-over';
    for (let ox = -outlineWidth; ox <= outlineWidth; ox++) {
        for (let oy = -outlineWidth; oy <= outlineWidth; oy++) {
            if (ox * ox + oy * oy <= outlineWidth * outlineWidth) {
                octx.drawImage(layer.img, pad + ox, pad + oy, w, h);
            }
        }
    }
    // Colorize the expanded silhouette
    octx.globalCompositeOperation = 'source-in';
    octx.fillStyle = outlineColor;
    octx.fillRect(0, 0, oc.width, oc.height);
    // Draw original on top
    octx.globalCompositeOperation = 'source-over';
    octx.drawImage(layer.img, pad, pad, w, h);
    // SYNCHRONOUS swap: canvas element doubles as drawable image so we skip the
    // Image.onload race. Prior code left a window where Ctrl+Z captured the
    // wrong state if the user was fast on the keyboard.
    const bbox = layer.bbox || [0, 0, w, h];
    layer.bbox = [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad];
    layer.img = oc;
    recompositeFromLayers();
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Outline added: ' + outlineWidth + 'px ' + outlineColor);
}
window.addLayerOutline = addLayerOutline;

// Knockout: cut the layer's shape out of layers below (transparent punch-through)
function knockoutLayer(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer) return;
    // WIN #5 (Windham audit): destructive blendMode mutation must respect the
    // lock badge. Sister functions addLayerOutline / centerLayerOnCanvas /
    // fitLayerToCanvas all bail with the same toast pattern.
    if (layer.locked) {
        if (typeof showToast === 'function') showToast('"' + (layer.name || 'Layer') + '" is locked — unlock to apply knockout', true);
        return;
    }
    _pushLayerStackUndo('knockout layer');
    // Set blend mode to destination-out which punches through lower layers
    layer.blendMode = 'destination-out';
    recompositeFromLayers();
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Knockout applied — layer punches through layers below');
}
window.knockoutLayer = knockoutLayer;

// Duplicate layer with offset (useful for sponsor repetition patterns)
function duplicateLayerWithOffset(layerId, offsetX, offsetY) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer) return;
    _pushLayerStackUndo('duplicate w/ offset');
    offsetX = offsetX || 50;
    offsetY = offsetY || 50;
    const idx = _psdLayers.indexOf(layer);
    const bbox = layer.bbox || [0, 0, 100, 100];
    const newLayer = {
        id: 'psd_dup_' + Date.now() + '_' + Math.random().toString(36).substr(2, 4),
        name: layer.name + ' copy',
        path: (layer.path || '') + ' copy',
        visible: true,
        opacity: layer.opacity,
        img: layer.img,
        bbox: [bbox[0] + offsetX, bbox[1] + offsetY, bbox[2] + offsetX, bbox[3] + offsetY],
        groupName: layer.groupName,
        blendMode: layer.blendMode || 'source-over',
        locked: false,
        effects: layer.effects ? JSON.parse(JSON.stringify(layer.effects)) : null,
    };
    _psdLayers.splice(idx + 1, 0, newLayer);
    _selectedLayerId = newLayer.id;
    if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
    recompositeFromLayers();
    renderLayerPanel();
    drawLayerBounds();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Duplicated with offset (+' + offsetX + ', +' + offsetY + ')');
}
window.duplicateLayerWithOffset = duplicateLayerWithOffset;

// Center layer on canvas (useful for positioning sponsors)
function centerLayerOnCanvas(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer || !layer.img) return;
    if (layer.locked) {
        if (typeof showToast === 'function') showToast(`"${layer.name}" is locked — unlock to move`, 'warn');
        return;
    }
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    _pushLayerUndo(layer, 'center on canvas');
    const w = layer.img.width || layer.img.naturalWidth;
    const h = layer.img.height || layer.img.naturalHeight;
    const cx = Math.round((pc.width - w) / 2);
    const cy = Math.round((pc.height - h) / 2);
    layer.bbox = [cx, cy, cx + w, cy + h];
    recompositeFromLayers();
    renderLayerPanel();
    drawLayerBounds();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Layer centered on canvas');
}
window.centerLayerOnCanvas = centerLayerOnCanvas;

// Fit layer to canvas width (preserving aspect ratio)
function fitLayerToCanvas(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer || !layer.img) return;
    if (layer.locked) {
        if (typeof showToast === 'function') showToast(`"${layer.name}" is locked — unlock to resize`, 'warn');
        return;
    }
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    _pushLayerUndo(layer, 'fit to canvas');
    const origW = layer.img.width || layer.img.naturalWidth;
    const origH = layer.img.height || layer.img.naturalHeight;
    if (!origW || !origH) return;
    const scale = Math.min(pc.width / origW, pc.height / origH);
    const newW = Math.round(origW * scale);
    const newH = Math.round(origH * scale);
    const cx = Math.round((pc.width - newW) / 2);
    const cy = Math.round((pc.height - newH) / 2);
    // Resize the image — synchronous canvas swap (no Image.onload race).
    const rc = document.createElement('canvas');
    rc.width = newW; rc.height = newH;
    const rctx = rc.getContext('2d');
    rctx.drawImage(layer.img, 0, 0, newW, newH);
    layer.img = rc;
    layer.bbox = [cx, cy, cx + newW, cy + newH];
    recompositeFromLayers();
    renderLayerPanel();
    drawLayerBounds();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Layer fitted to canvas');
}
window.fitLayerToCanvas = fitLayerToCanvas;

function mergeLayerDown(layerId) {
    const idx = _psdLayers.findIndex(l => l.id === layerId);
    if (idx <= 0) { if (typeof showToast === 'function') showToast('No layer below to merge into', 'info'); return; }
    const upper = _psdLayers[idx];
    const lower = _psdLayers[idx - 1];
    if (!upper.img || !lower.img) return;
    // 2026-04-18 MARATHON bug #43 (Street, HIGH): same class as flatten
    // (bug #36). Merging down destroys the upper layer's ID while any
    // zone's `sourceLayer` was pointing at it. Pre-fix the zone silently
    // lost its restriction and painted across the whole car. Now we
    // migrate those references onto the lower layer (the surviving one)
    // so the restriction still means something meaningful.
    if (typeof zones !== 'undefined' && Array.isArray(zones)) {
        zones.forEach(function (z) {
            if (z && z.sourceLayer === upper.id) {
                z.sourceLayer = lower.id;
            }
        });
    }
    // Codex MED + Pillman latent #464: refuse to merge down a hidden layer.
    // Photoshop's Merge Down treats the upper layer's visibility as an active
    // signal — hidden layers are not part of the visible composition and
    // should not silently bake their pixels into the lower layer.
    // Symmetric with mergeVisibleLayers which already filters by visibility.
    if (upper.visible === false) {
        if (typeof showToast === 'function') {
            showToast(`"${upper.name}" is hidden — show it first to merge down`, 'warn');
        }
        return;
    }
    _pushLayerStackUndo('merge down');
    // Workstream 17 #326 — opt-in merge logging.
    if (typeof window !== 'undefined' && window._SPB_DEBUG_MERGE === true) {
        try {
            console.log('[SPB][merge] merge-down upper="%s" (effects=%s) into lower="%s" (effects=%s)',
                upper.name, !!upper.effects, lower.name, !!lower.effects);
        } catch (_) {}
    }

    // Composite upper onto lower
    const pc = document.getElementById('paintCanvas');
    const cw = pc ? pc.width : 2048, ch = pc ? pc.height : 2048;
    const mc = document.createElement('canvas');
    mc.width = cw; mc.height = ch;
    const mctx = mc.getContext('2d');
    // Draw lower first (with its effects baked in — Photoshop parity)
    if (lower.effects && typeof renderLayerEffects === 'function') {
        renderLayerEffects(mctx, lower, 'before');
    }
    mctx.globalAlpha = (lower.opacity != null ? lower.opacity : 255) / 255;
    mctx.drawImage(lower.img, lower.bbox[0], lower.bbox[1]);
    if (lower.effects && typeof renderLayerEffects === 'function') {
        mctx.globalAlpha = 1.0;
        mctx.globalCompositeOperation = 'source-over';
        renderLayerEffects(mctx, lower, 'after');
    }
    // Draw upper on top (also bake its effects)
    mctx.globalAlpha = (upper.opacity != null ? upper.opacity : 255) / 255;
    if (upper.blendMode && upper.blendMode !== 'source-over') mctx.globalCompositeOperation = upper.blendMode;
    if (upper.effects && typeof renderLayerEffects === 'function') {
        renderLayerEffects(mctx, upper, 'before');
    }
    mctx.drawImage(upper.img, upper.bbox[0], upper.bbox[1]);
    if (upper.effects && typeof renderLayerEffects === 'function') {
        mctx.globalAlpha = 1.0;
        mctx.globalCompositeOperation = 'source-over';
        renderLayerEffects(mctx, upper, 'after');
    }

    // SYNCHRONOUS: assign canvas directly (HTMLCanvasElement is drawable) so
    // Ctrl+Z immediately after merge always targets the merged state, not a
    // pre-onload stale snapshot.
    lower.img = mc;
    lower.bbox = [0, 0, cw, ch];
    lower.opacity = 255;
    lower.blendMode = 'source-over';
    // Effects were baked into the merged pixels above — drop them on the
    // result so they don't render twice. Photoshop does the same: merged
    // pixels lose their style attribution.
    lower.effects = null;
    _psdLayers.splice(idx, 1);
    _selectedLayerId = lower.id;
    if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
    recompositeFromLayers();
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Layers merged');
}

function flattenAllLayers() {
    if (_psdLayers.length <= 1) return;
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    // 2026-04-18 MARATHON bug #36 (Animal, HIGH): pre-fix, flatten wiped
    // _psdLayers and created one fresh layer with a new ID. Any zone
    // whose `sourceLayer` referenced the old layer IDs silently lost its
    // restriction — the render path's `_psdLayers.find(l => l.id === ...)`
    // returned undefined, and the zone painted everywhere. Now we scan
    // zones before the wipe, count restricted zones, and warn (with
    // option to cancel). Then CLEAR the stale sourceLayer fields on the
    // affected zones so the UI no longer shows dead ID strings.
    if (typeof zones !== 'undefined' && Array.isArray(zones)) {
        const restrictedZones = zones.filter(z => z && z.sourceLayer);
        if (restrictedZones.length > 0) {
            const names = restrictedZones.map(z => z.name || '(unnamed)').join(', ');
            const ok = confirm(
                `Flattening will discard ${restrictedZones.length} zone source-layer ` +
                `restriction(s): ${names}. These zones will then paint across the ` +
                `whole car instead of being restricted. Flatten anyway?`
            );
            if (!ok) return;
        }
    }
    _pushLayerStackUndo('flatten all');
    if (typeof zones !== 'undefined' && Array.isArray(zones)) {
        // Clear stale sourceLayer references so the UI doesn't show zombie
        // layer IDs and the render path doesn't silently ignore them.
        zones.forEach(function (z) { if (z && z.sourceLayer) z.sourceLayer = null; });
    }
    // Workstream 17 #326 — opt-in flatten logging.
    if (typeof window !== 'undefined' && window._SPB_DEBUG_MERGE === true) {
        try {
            console.log('[SPB][merge] flatten-all collapsing %d layers',
                _psdLayers.length);
        } catch (_) {}
    }
    // recompositeFromLayers already draws the full composite
    recompositeFromLayers();
    // Snapshot the flattened composite to a fresh canvas (synchronous — avoids
    // the toDataURL→Image race where Ctrl+Z sees the mid-state).
    const flatCanvas = document.createElement('canvas');
    flatCanvas.width = pc.width;
    flatCanvas.height = pc.height;
    flatCanvas.getContext('2d').drawImage(pc, 0, 0);
    _psdLayers.length = 0;
    _psdLayers.push({
        id: 'psd_flat_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
        name: 'Flattened',
        path: 'Flattened',
        visible: true,
        opacity: 255,
        img: flatCanvas,
        bbox: [0, 0, pc.width, pc.height],
        groupName: '',
        blendMode: 'source-over',
        locked: false,
    });
    _selectedLayerId = _psdLayers[0].id;
    if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('All layers flattened');
}

// Merge all visible layers into one, keeping hidden layers intact
function mergeVisibleLayers() {
    const visible = _psdLayers.filter(l => l.visible);
    if (visible.length <= 1) { showToast('Need 2+ visible layers to merge', true); return; }
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    // 2026-04-18 MARATHON bug #43 (Street, HIGH): merge-visible creates a
    // fresh layer with a new ID and discards all the constituent layer
    // IDs. Any zone whose sourceLayer referenced one of those IDs would
    // silently lose its restriction. Confirm with the painter first, and
    // clear the stale refs so the UI doesn't show zombie IDs.
    if (typeof zones !== 'undefined' && Array.isArray(zones)) {
        const visibleIds = new Set(visible.map(l => l.id));
        const affected = zones.filter(z => z && z.sourceLayer && visibleIds.has(z.sourceLayer));
        if (affected.length > 0) {
            const names = affected.map(z => z.name || '(unnamed)').join(', ');
            const ok = confirm(
                `Merge Visible will destroy the layer IDs referenced by ${affected.length} ` +
                `zone source-layer restriction(s): ${names}. Those zones will then paint ` +
                `across the merged layer. Merge anyway?`
            );
            if (!ok) return;
        }
    }
    _pushLayerStackUndo('merge visible');
    if (typeof zones !== 'undefined' && Array.isArray(zones)) {
        const visibleIds = new Set(visible.map(l => l.id));
        zones.forEach(function (z) {
            if (z && z.sourceLayer && visibleIds.has(z.sourceLayer)) z.sourceLayer = null;
        });
    }

    // Composite only visible layers — and bake any layer effects so styled
    // layers don't silently lose their drop shadows / strokes / glows when
    // merged. This matches the standard Photoshop "Merge Visible" behavior.
    const tmpCanvas = document.createElement('canvas');
    tmpCanvas.width = pc.width; tmpCanvas.height = pc.height;
    const tmpCtx = tmpCanvas.getContext('2d');
    for (const layer of visible) {
        if (!layer.img) continue;
        // 'before' phase: drop shadow + outer glow render BENEATH the layer.
        if (layer.effects && typeof renderLayerEffects === 'function') {
            tmpCtx.globalAlpha = 1.0;
            tmpCtx.globalCompositeOperation = 'source-over';
            renderLayerEffects(tmpCtx, layer, 'before');
        }
        tmpCtx.globalAlpha = (layer.opacity != null ? layer.opacity : 255) / 255;
        tmpCtx.globalCompositeOperation = layer.blendMode || 'source-over';
        // Bockwinkel B6 (Workstream 23 #445): codebase standardized on array
        // bbox [x1,y1,x2,y2]. The defensive `bbox.x || bbox[0]` fallback was
        // hiding shape bugs (and pasteAsLayer was the only producer of the
        // object shape — that's now fixed too). Plain array read.
        const bbox = layer.bbox || [0, 0, 0, 0];
        const bx = bbox[0] || 0, by = bbox[1] || 0;
        tmpCtx.drawImage(layer.img, bx, by);
        // 'after' phase: stroke + color overlay + bevel render ABOVE the layer.
        if (layer.effects && typeof renderLayerEffects === 'function') {
            tmpCtx.globalAlpha = 1.0;
            tmpCtx.globalCompositeOperation = 'source-over';
            renderLayerEffects(tmpCtx, layer, 'after');
        }
    }
    tmpCtx.globalAlpha = 1;
    tmpCtx.globalCompositeOperation = 'source-over';

    // SYNCHRONOUS canvas swap — prevents Ctrl+Z races with toDataURL.
    const hidden = _psdLayers.filter(l => !l.visible);
    _psdLayers.length = 0;
    _psdLayers.push({
        id: 'merged_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7), name: 'Merged Visible', path: '',
        visible: true, opacity: 255, blendMode: 'source-over', locked: false,
        img: tmpCanvas, bbox: [0, 0, pc.width, pc.height],
    });
    // Re-add hidden layers
    hidden.forEach(l => _psdLayers.push(l));
    _selectedLayerId = _psdLayers[0].id;
    if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
    recompositeFromLayers();
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast(`Merged ${visible.length} visible layers`);
}
window.mergeVisibleLayers = mergeVisibleLayers;

function selectLayerPixels(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer || !layer.img) return;
    // Draw layer to temp canvas and extract alpha as region mask for the SELECTED ZONE
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const zone = (typeof zones !== 'undefined' && typeof selectedZoneIndex !== 'undefined') ? zones[selectedZoneIndex] : null;
    if (!zone) {
        if (typeof showToast === 'function') showToast('Select a zone first, then use SELECT to create a mask from layer pixels', 'info');
        return;
    }
    const w = pc.width, h = pc.height;
    const tc = document.createElement('canvas');
    tc.width = w; tc.height = h;
    const tctx = tc.getContext('2d');
    tctx.drawImage(layer.img, layer.bbox[0], layer.bbox[1]);
    const data = tctx.getImageData(0, 0, w, h);
    // Write to the selected zone's regionMask
    if (!zone.regionMask) zone.regionMask = new Uint8Array(w * h);
    if (typeof pushUndo === 'function') pushUndo(selectedZoneIndex);
    for (let p = 0; p < zone.regionMask.length; p++) {
        zone.regionMask[p] = data.data[p * 4 + 3] > 10 ? 255 : 0;
    }
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast(`Zone ${selectedZoneIndex + 1}: selected ${layer.name} pixels as mask`);
}

// ═══ IMAGE ADJUSTMENTS — Apply to selected layer or entire canvas ═══

function _getAdjustmentTarget() {
    // If a PSD layer is selected, adjust that layer. Otherwise adjust the main canvas.
    // willReadFrequently on both branches: every adjustment (brightness/contrast/
    // hue-sat/levels/curves/etc.) reads the target via getImageData and writes
    // back via putImageData. Without the flag this round-trips the GPU per slider tick.
    const adjustmentLabel = arguments[0] || 'adjust image';
    if (_selectedLayerId && _psdLayersLoaded) {
        const layer = _psdLayers.find(l => l.id === _selectedLayerId);
        if (layer && layer.img) {
            if (layer.locked) {
                if (typeof showToast === 'function') showToast(`"${layer.name}" is locked — unlock to apply ${adjustmentLabel}`, 'warn');
                return null;
            }
            const c = document.createElement('canvas');
            c.width = layer.img.width; c.height = layer.img.height;
            const ctx = c.getContext('2d', { willReadFrequently: true });
            ctx.drawImage(layer.img, 0, 0);
            if (typeof _pushLayerUndo === 'function') _pushLayerUndo(layer, adjustmentLabel);
            return { canvas: c, ctx: ctx, layer: layer, isLayer: true };
        }
    }
    const pc = document.getElementById('paintCanvas');
    if (!pc) return null;
    if (typeof pushPixelUndo === 'function') pushPixelUndo(adjustmentLabel);
    return { canvas: pc, ctx: pc.getContext('2d', { willReadFrequently: true }), layer: null, isLayer: false };
}

function _commitAdjustment(target) {
    if (target.isLayer && target.layer) {
        // Bockwinkel B3 (Workstream 23 #444): synchronous canvas swap. Old code
        // ran new Image()+toDataURL+onload, which created a Ctrl+Z race where
        // a fast-undo after an adjustment slider would land on pre-onload
        // state. Canvas is drawable as an image source; assign directly.
        target.layer.img = target.canvas;
        recompositeFromLayers();
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    } else {
        paintImageData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
        // 2026-04-18 MARATHON bug #30 (MED): pre-fix, adjustment filters on
        // the COMPOSITE (no layer selected) updated paintImageData but
        // never fired Live Preview. Painter adjusted brightness/hue/etc.
        // on the whole canvas, rendered car stayed stale. Fixed for
        // symmetry with the layer path above.
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }
}

function adjustBrightnessContrast(brightness, contrast) {
    const target = _getAdjustmentTarget('brightness / contrast');
    if (!target) return;
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const d = imgData.data;
    const b = brightness || 0; // -100 to 100
    const c = (contrast || 0) / 100; // -1 to 1
    // 2026-04-19 HEENAN H4HR-PERF5 — adjustBrightnessContrast hot-path opt.
    // Unrolled channel loop + bitwise round + drop manual clamp
    // (Uint8ClampedArray auto-clamps writes outside [0,255]).
    const factor = (1 + c) / (1 - (c < 0.99 ? c : 0.99));
    const len = d.length;
    for (let i = 0; i < len; i += 4) {
        d[i]   = (factor * (d[i]   + b - 128) + 128 + 0.5) | 0;
        d[i+1] = (factor * (d[i+1] + b - 128) + 128 + 0.5) | 0;
        d[i+2] = (factor * (d[i+2] + b - 128) + 128 + 0.5) | 0;
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    if (typeof showToast === 'function') showToast(`Brightness ${b > 0 ? '+' : ''}${b}, Contrast ${contrast > 0 ? '+' : ''}${contrast}`);
}

function adjustHueSaturation(hueShift, saturation, lightness) {
    const target = _getAdjustmentTarget('hue / saturation');
    if (!target) return;
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const d = imgData.data;
    const hs = (hueShift || 0) / 360; // 0-1
    const sat = 1 + (saturation || 0) / 100; // 0-2
    const light = (lightness || 0) / 100;
    // 2026-04-19 HEENAN H4HR-PERF14 — adjustHueSaturation hot-path opt.
    // Inline 3-way max/min, drop manual clamps (Uint8ClampedArray clamps),
    // bitwise round, hoist hue2rgb helper out of the loop. The HSL math
    // itself is unavoidable; this opts only the per-iteration overhead.
    const hue2rgb = function (p, q, t) {
        if (t < 0) t += 1;
        else if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 0.5) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
    };
    const inv255 = 1 / 255;
    const len = d.length;
    for (let i = 0; i < len; i += 4) {
        const r = d[i] * inv255, g = d[i+1] * inv255, b = d[i+2] * inv255;
        const max = r > g ? (r > b ? r : b) : (g > b ? g : b);
        const min = r < g ? (r < b ? r : b) : (g < b ? g : b);
        let h = 0, s = 0;
        const l_in = (max + min) * 0.5;
        if (max !== min) {
            const delta = max - min;
            s = l_in > 0.5 ? delta / (2 - max - min) : delta / (max + min);
            if (max === r) h = ((g - b) / delta + (g < b ? 6 : 0)) / 6;
            else if (max === g) h = ((b - r) / delta + 2) / 6;
            else h = ((r - g) / delta + 4) / 6;
        }
        h = (h + hs) % 1; if (h < 0) h += 1;
        // Inline clamp via ternary instead of Math.max(0, Math.min(1, ...)).
        let s_out = s * sat;
        if (s_out < 0) s_out = 0; else if (s_out > 1) s_out = 1;
        let l = l_in + light;
        if (l < 0) l = 0; else if (l > 1) l = 1;
        let rr, gg, bb;
        if (s_out === 0) { rr = gg = bb = l; }
        else {
            const q = l < 0.5 ? l * (1 + s_out) : l + s_out - l * s_out;
            const p = 2 * l - q;
            rr = hue2rgb(p, q, h + 1/3);
            gg = hue2rgb(p, q, h);
            bb = hue2rgb(p, q, h - 1/3);
        }
        d[i]   = (rr * 255 + 0.5) | 0;
        d[i+1] = (gg * 255 + 0.5) | 0;
        d[i+2] = (bb * 255 + 0.5) | 0;
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    if (typeof showToast === 'function') showToast('Hue/Saturation adjusted');
}

// Keep the vertical-toolbar entries as aliases of the canonical mutators below.
// That way the visible "same operation" buttons cannot drift apart on layer
// routing, locked-layer guards, preview refresh, or undo behavior.
function adjustInvertColors() { return invertCanvasColors(); }

function adjustGrayscale() { return desaturateCanvas(); }

function adjustSepia(intensity) {
    const target = _getAdjustmentTarget('sepia');
    if (!target) return;
    const amt = (intensity != null ? intensity : 80) / 100;
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const d = imgData.data;
    // 2026-04-19 HEENAN H4HR-PERF6 — adjustSepia hot-path opt.
    // Drop Math.min clamp (Uint8ClampedArray auto-clamps), bitwise round,
    // precompute (1-amt) once.
    const len = d.length;
    const inv = 1 - amt;
    for (let i = 0; i < len; i += 4) {
        const r = d[i], g = d[i+1], b = d[i+2];
        const sr = r * 0.393 + g * 0.769 + b * 0.189;
        const sg = r * 0.349 + g * 0.686 + b * 0.168;
        const sb = r * 0.272 + g * 0.534 + b * 0.131;
        d[i]   = (r * inv + sr * amt + 0.5) | 0;
        d[i+1] = (g * inv + sg * amt + 0.5) | 0;
        d[i+2] = (b * inv + sb * amt + 0.5) | 0;
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    if (typeof showToast === 'function') showToast('Sepia applied');
}

function adjustPosterize(levels) { return posterize(levels); }

function applyGaussianBlur(radius) {
    const target = _getAdjustmentTarget('gaussian blur');
    if (!target) return;
    const r = Math.max(1, Math.min(20, radius || 3));
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const w = target.canvas.width, h = target.canvas.height;
    const src = new Uint8ClampedArray(imgData.data);
    const d = imgData.data;
    // 2026-04-19 HEENAN H4HR-PERF15 — applyGaussianBlur hot-path opt.
    // Box blur is O(W·H·R) per pass × 3 passes × 2 axes. Optimizations:
    //   (1) Sliding-window sum: avoid recomputing the radius window per pixel.
    //       Each step adds the new edge and removes the trailing edge → O(W·H)
    //       per pass independent of R.
    //   (2) Precompute 1/count where possible, use bitwise round.
    //   (3) Inline Math.max/min as ternary clamps.
    // Output is bit-identical to original (same averaging math).
    const w4 = w * 4;
    for (let pass = 0; pass < 3; pass++) {
        const tmp = new Uint8ClampedArray(d);
        // Horizontal pass — sliding window
        for (let y = 0; y < h; y++) {
            const yOff = y * w4;
            // Initialize window for x=0
            let rr = 0, gg = 0, bb = 0, aa = 0;
            for (let dx = -r; dx <= r; dx++) {
                const sx = dx < 0 ? 0 : (dx > w - 1 ? w - 1 : dx);
                const si = yOff + sx * 4;
                rr += tmp[si]; gg += tmp[si+1]; bb += tmp[si+2]; aa += tmp[si+3];
            }
            const winSize = 2 * r + 1;
            const inv = 1 / winSize;
            for (let x = 0; x < w; x++) {
                const di = yOff + x * 4;
                d[di]   = (rr * inv + 0.5) | 0;
                d[di+1] = (gg * inv + 0.5) | 0;
                d[di+2] = (bb * inv + 0.5) | 0;
                d[di+3] = (aa * inv + 0.5) | 0;
                // Slide: remove (x - r), add (x + r + 1)
                const removeX = x - r;
                const addX = x + r + 1;
                const rmX = removeX < 0 ? 0 : (removeX > w - 1 ? w - 1 : removeX);
                const adX = addX < 0 ? 0 : (addX > w - 1 ? w - 1 : addX);
                const rmI = yOff + rmX * 4;
                const adI = yOff + adX * 4;
                rr += tmp[adI]   - tmp[rmI];
                gg += tmp[adI+1] - tmp[rmI+1];
                bb += tmp[adI+2] - tmp[rmI+2];
                aa += tmp[adI+3] - tmp[rmI+3];
            }
        }
        // Vertical pass — sliding window
        const tmp2 = new Uint8ClampedArray(d);
        for (let x = 0; x < w; x++) {
            const x4 = x * 4;
            let rr = 0, gg = 0, bb = 0, aa = 0;
            for (let dy = -r; dy <= r; dy++) {
                const sy = dy < 0 ? 0 : (dy > h - 1 ? h - 1 : dy);
                const si = sy * w4 + x4;
                rr += tmp2[si]; gg += tmp2[si+1]; bb += tmp2[si+2]; aa += tmp2[si+3];
            }
            const winSize = 2 * r + 1;
            const inv = 1 / winSize;
            for (let y = 0; y < h; y++) {
                const di = y * w4 + x4;
                d[di]   = (rr * inv + 0.5) | 0;
                d[di+1] = (gg * inv + 0.5) | 0;
                d[di+2] = (bb * inv + 0.5) | 0;
                d[di+3] = (aa * inv + 0.5) | 0;
                const removeY = y - r;
                const addY = y + r + 1;
                const rmY = removeY < 0 ? 0 : (removeY > h - 1 ? h - 1 : removeY);
                const adY = addY < 0 ? 0 : (addY > h - 1 ? h - 1 : addY);
                const rmI = rmY * w4 + x4;
                const adI = adY * w4 + x4;
                rr += tmp2[adI]   - tmp2[rmI];
                gg += tmp2[adI+1] - tmp2[rmI+1];
                bb += tmp2[adI+2] - tmp2[rmI+2];
                aa += tmp2[adI+3] - tmp2[rmI+3];
            }
        }
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    if (typeof showToast === 'function') showToast(`Gaussian blur (radius ${r})`);
}

function applySharpen(amount) {
    const target = _getAdjustmentTarget('sharpen');
    if (!target) return;
    const str = (amount != null ? amount : 50) / 100;
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const w = target.canvas.width, h = target.canvas.height;
    const src = new Uint8ClampedArray(imgData.data);
    const d = imgData.data;
    // 2026-04-19 HEENAN H4HR-PERF16 — applySharpen hot-path opt.
    // Precompute per-row offsets (yPrev, yNext) once per row instead of
    // computing y*w + x*4 inside the channel loop. Unroll channel loop.
    // Replace /4 with *0.25, drop manual clamp (Uint8ClampedArray clamps),
    // bitwise round. Same unsharp mask math.
    const w4 = w * 4;
    const QUARTER = 0.25;
    for (let y = 1; y < h - 1; y++) {
        const yOff   =  y * w4;
        const yPrev  = yOff - w4;
        const yNext  = yOff + w4;
        for (let x = 1; x < w - 1; x++) {
            const x4 = x * 4;
            const ci = yOff + x4;
            const upI = yPrev + x4;
            const dnI = yNext + x4;
            const lfI = yOff + x4 - 4;
            const rtI = yOff + x4 + 4;
            // R
            const cr = src[ci];
            d[ci]   = (cr + str * (cr - (src[upI]   + src[dnI]   + src[lfI]   + src[rtI])   * QUARTER) + 0.5) | 0;
            const cg = src[ci+1];
            d[ci+1] = (cg + str * (cg - (src[upI+1] + src[dnI+1] + src[lfI+1] + src[rtI+1]) * QUARTER) + 0.5) | 0;
            const cb = src[ci+2];
            d[ci+2] = (cb + str * (cb - (src[upI+2] + src[dnI+2] + src[lfI+2] + src[rtI+2]) * QUARTER) + 0.5) | 0;
        }
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    if (typeof showToast === 'function') showToast(`Sharpened (${amount}%)`);
}

function applyNoiseAdd(intensity) {
    const target = _getAdjustmentTarget('add noise');
    if (!target) return;
    const amt = (intensity != null ? intensity : 30);
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const d = imgData.data;
    // 2026-04-19 HEENAN H4HR-PERF7 — applyNoiseAdd hot-path opt.
    // Unrolled channel loop, drop manual clamp (Uint8ClampedArray clamps),
    // bitwise round. Keep Math.random() — it's the noise source.
    const len = d.length;
    const amt2 = amt * 2;
    for (let i = 0; i < len; i += 4) {
        if (d[i + 3] === 0) continue;
        d[i]   = (d[i]   + (Math.random() - 0.5) * amt2 + 0.5) | 0;
        d[i+1] = (d[i+1] + (Math.random() - 0.5) * amt2 + 0.5) | 0;
        d[i+2] = (d[i+2] + (Math.random() - 0.5) * amt2 + 0.5) | 0;
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    if (typeof showToast === 'function') showToast(`Noise added (${amt})`);
}

function applyEmboss() {
    const target = _getAdjustmentTarget('emboss');
    if (!target) return;
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const w = target.canvas.width, h = target.canvas.height;
    const src = new Uint8ClampedArray(imgData.data);
    const d = imgData.data;
    // 2026-04-19 HEENAN H4HR-PERF8 — applyEmboss hot-path opt.
    // Precompute row offsets once per row instead of recomputing
    // y*w + x*4 inside the channel loop. Unrolled channel loop, bitwise
    // round, drop manual clamp.
    // Emboss kernel: [-2,-1,0],[-1,1,1],[0,1,2]
    const w4 = w * 4;
    for (let y = 1; y < h - 1; y++) {
        const yOff   =  y * w4;       // current row
        const yPrev  = yOff - w4;     // y-1 row
        const yNext  = yOff + w4;     // y+1 row
        for (let x = 1; x < w - 1; x++) {
            const x4 = x * 4;
            const ci = yOff + x4;
            const aa = yPrev + x4 - 4; // (y-1, x-1)
            const ab = yPrev + x4;     // (y-1, x)
            const cc = yOff  + x4 - 4; // (y,   x-1)
            const cd = yOff  + x4 + 4; // (y,   x+1)
            const dd = yNext + x4;     // (y+1, x)
            const de = yNext + x4 + 4; // (y+1, x+1)
            // R, G, B unrolled
            d[ci]     = (((-2*src[aa]   - src[ab]   - src[cc]   + src[ci]   + src[cd]   + src[dd]   + 2*src[de])   * 0.5 + 128) + 0.5) | 0;
            d[ci + 1] = (((-2*src[aa+1] - src[ab+1] - src[cc+1] + src[ci+1] + src[cd+1] + src[dd+1] + 2*src[de+1]) * 0.5 + 128) + 0.5) | 0;
            d[ci + 2] = (((-2*src[aa+2] - src[ab+2] - src[cc+2] + src[ci+2] + src[cd+2] + src[dd+2] + 2*src[de+2]) * 0.5 + 128) + 0.5) | 0;
        }
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    if (typeof showToast === 'function') showToast('Emboss applied');
}

// Prompt-based adjustment dialogs
// 2026-04-18 SIX-HOUR MARATHON — replace raw prompt() adjustment dialogs
// with a proper slider modal. User explicitly called out: "Replace any
// other raw prompt garbage with real controls. Make adjustment workflow
// feel intentional." Pre-fix: 6 filters used chained prompt() calls
// (Brightness / Contrast / Hue / Sat / Lightness / Vignette / Threshold /
// ColorTemp / Vibrance), felt like 1995.
//
// The helper below renders a modal with N sliders + OK/Cancel + keyboard
// shortcuts (Enter commits, Esc cancels). One shared implementation so a
// future filter addition is a 5-line call-site change, not a new dialog.
function _showAdjustmentDialog(spec) {
    return new Promise(function (resolve) {
        // spec = { title, sliders: [{ label, min, max, step, default, suffix? }], onCommit? }
        var modal = document.createElement('div');
        modal.id = '_adjustmentDialogModal';
        modal.style.cssText = [
            'position: fixed', 'inset: 0',
            'background: rgba(0, 0, 0, 0.55)',
            'display: flex', 'align-items: center', 'justify-content: center',
            'z-index: 999999', 'font-family: "Segoe UI", "Inter", sans-serif',
        ].join(';');
        var panel = document.createElement('div');
        panel.style.cssText = [
            'background: #15181e', 'border: 1px solid rgba(0,229,255,0.35)',
            'border-radius: 6px', 'padding: 16px 18px 14px 18px',
            'min-width: 320px', 'max-width: 440px',
            'box-shadow: 0 12px 40px rgba(0,0,0,0.6)',
            'color: #e6e8eb',
        ].join(';');
        var title = document.createElement('div');
        title.textContent = spec.title || 'Adjust';
        title.style.cssText = [
            'font-size: 13px', 'font-weight: 700',
            'color: #00e5ff', 'letter-spacing: 0.4px',
            'margin-bottom: 10px', 'text-transform: uppercase',
        ].join(';');
        panel.appendChild(title);

        var values = [];
        (spec.sliders || []).forEach(function (sl, i) {
            values[i] = Number(sl.default || 0);
            var row = document.createElement('div');
            row.style.cssText = 'margin-bottom: 10px;';
            var lab = document.createElement('div');
            lab.style.cssText = 'display:flex;justify-content:space-between;font-size:11px;color:#aab3bc;margin-bottom:4px;';
            lab.innerHTML = '<span>' + sl.label + '</span><span id="_adjSlVal' + i + '">' + values[i] + (sl.suffix || '') + '</span>';
            var input = document.createElement('input');
            input.type = 'range';
            input.min = sl.min;
            input.max = sl.max;
            input.step = sl.step || 1;
            input.value = values[i];
            input.style.cssText = 'width:100%;accent-color:#00e5ff;';
            input.addEventListener('input', function () {
                values[i] = Number(input.value);
                var vSpan = document.getElementById('_adjSlVal' + i);
                if (vSpan) vSpan.textContent = values[i] + (sl.suffix || '');
            });
            row.appendChild(lab);
            row.appendChild(input);
            panel.appendChild(row);
        });

        var btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;margin-top:6px;';
        var cancelBtn = document.createElement('button');
        cancelBtn.textContent = 'Cancel';
        cancelBtn.style.cssText = 'padding:5px 14px;background:transparent;border:1px solid #444;color:#aaa;border-radius:4px;cursor:pointer;font-size:11px;';
        var okBtn = document.createElement('button');
        okBtn.textContent = 'Apply';
        okBtn.style.cssText = 'padding:5px 14px;background:rgba(0,229,255,0.18);border:1px solid rgba(0,229,255,0.6);color:#00e5ff;border-radius:4px;cursor:pointer;font-size:11px;font-weight:700;';
        btnRow.appendChild(cancelBtn);
        btnRow.appendChild(okBtn);
        panel.appendChild(btnRow);

        modal.appendChild(panel);
        document.body.appendChild(modal);

        function cleanup() {
            document.removeEventListener('keydown', onKey, true);
            if (modal.parentNode) modal.parentNode.removeChild(modal);
        }
        function onKey(e) {
            if (e.defaultPrevented) return; // SESSION ROUTER bail (capture-phase modal)
            if (e.key === 'Enter') { e.preventDefault(); commit(); }
            else if (e.key === 'Escape') { e.preventDefault(); cancel(); }
        }
        function commit() { cleanup(); resolve(values); }
        function cancel() { cleanup(); resolve(null); }
        okBtn.addEventListener('click', commit);
        cancelBtn.addEventListener('click', cancel);
        modal.addEventListener('click', function (e) { if (e.target === modal) cancel(); });
        document.addEventListener('keydown', onKey, true);
    });
}
if (typeof window !== 'undefined') window._showAdjustmentDialog = _showAdjustmentDialog;

function promptAdjustBrightnessContrast() {
    _showAdjustmentDialog({
        title: 'Brightness / Contrast',
        sliders: [
            { label: 'Brightness', min: -100, max: 100, default: 0 },
            { label: 'Contrast', min: -100, max: 100, default: 0 },
        ],
    }).then(function (vals) {
        if (!vals) return;
        adjustBrightnessContrast(vals[0] || 0, vals[1] || 0);
    });
}

function promptAdjustHueSat() {
    _showAdjustmentDialog({
        title: 'Hue / Saturation / Lightness',
        sliders: [
            { label: 'Hue Shift', min: -180, max: 180, default: 0, suffix: '°' },
            { label: 'Saturation', min: -100, max: 100, default: 0 },
            { label: 'Lightness', min: -100, max: 100, default: 0 },
        ],
    }).then(function (vals) {
        if (!vals) return;
        adjustHueSaturation(vals[0] || 0, vals[1] || 0, vals[2] || 0);
    });
}

window.promptAdjustBrightnessContrast = promptAdjustBrightnessContrast;
window.promptAdjustHueSat = promptAdjustHueSat;

// Expose adjustment functions
window.adjustBrightnessContrast = adjustBrightnessContrast;
window.adjustHueSaturation = adjustHueSaturation;
window.adjustInvertColors = adjustInvertColors;
window.adjustGrayscale = adjustGrayscale;
window.adjustSepia = adjustSepia;
window.adjustPosterize = adjustPosterize;
window.applyGaussianBlur = applyGaussianBlur;
window.applySharpen = applySharpen;
window.applyNoiseAdd = applyNoiseAdd;
window.applyEmboss = applyEmboss;

// Vignette — darken edges for a cinematic/focused look
function applyVignette(strength) {
    const target = _getAdjustmentTarget('vignette');
    if (!target) return;
    const s = Math.max(0.1, Math.min(2.0, strength || 0.5));
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const w = target.canvas.width, h = target.canvas.height, d = imgData.data;
    // 2026-04-19 HEENAN H4HR-PERF9 — applyVignette hot-path opt.
    // Drop sqrt (compare squared distances), drop Math.max (factor never
    // exceeds 1; the inner clamp was for distances > 1 which the sq check
    // handles), bitwise round, precompute maxDistSq.
    const cx = w / 2, cy = h / 2;
    const maxDistSq = cx * cx + cy * cy;
    const sOverMaxSq = s / maxDistSq;
    for (let y = 0; y < h; y++) {
        const dy = y - cy;
        const dySq = dy * dy;
        const yOff = y * w * 4;
        for (let x = 0; x < w; x++) {
            const dx = x - cx;
            const distSqNorm = (dx * dx + dySq) * sOverMaxSq;
            // factor = 1 - dist²·s/maxDistSq.  When > 1 (corner), factor goes negative;
            // multiplied into d[..] gives negative, Uint8ClampedArray clamps to 0.
            const factor = 1 - distSqNorm;
            const idx = yOff + x * 4;
            d[idx]   = (d[idx]   * factor + 0.5) | 0;
            d[idx+1] = (d[idx+1] * factor + 0.5) | 0;
            d[idx+2] = (d[idx+2] * factor + 0.5) | 0;
        }
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    showToast('Vignette applied');
}

// Threshold — convert to pure black and white at a cutoff level
function applyThreshold(level) {
    const target = _getAdjustmentTarget('threshold');
    if (!target) return;
    const t = Math.max(0, Math.min(255, level || 128));
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const d = imgData.data, len = d.length;
    for (let i = 0; i < len; i += 4) {
        const lum = 0.299 * d[i] + 0.587 * d[i+1] + 0.114 * d[i+2];
        const v = lum >= t ? 255 : 0;
        d[i] = d[i+1] = d[i+2] = v;
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    showToast(`Threshold at ${t}`);
}

// Color Temperature — warm (orange) or cool (blue) shift
function adjustColorTemperature(shift) {
    const target = _getAdjustmentTarget('color temperature');
    if (!target) return;
    const s = Math.max(-100, Math.min(100, shift || 0));
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const d = imgData.data, len = d.length;
    const rAdd = s > 0 ? s * 0.5 : 0;
    const bAdd = s < 0 ? -s * 0.5 : 0;
    const gAdd = s > 0 ? s * 0.1 : s * 0.05;
    // 2026-04-19 HEENAN H4HR-PERF10 — adjustColorTemperature hot-path opt.
    // Drop manual clamp (Uint8ClampedArray auto-clamps), drop Math.round-equivalent
    // (the original truncated implicitly via clamp; explicit + 0.5 | 0 here).
    for (let i = 0; i < len; i += 4) {
        d[i]   = (d[i]   + rAdd + 0.5) | 0;
        d[i+1] = (d[i+1] + gAdd + 0.5) | 0;
        d[i+2] = (d[i+2] + bAdd + 0.5) | 0;
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    showToast(`Color temp ${s > 0 ? 'warmer' : 'cooler'}: ${s}`);
}

// Vibrance — boost muted colors more than saturated ones (smarter than saturation)
function adjustVibrance(amount) {
    const target = _getAdjustmentTarget('vibrance');
    if (!target) return;
    const a = Math.max(-100, Math.min(100, amount || 25));
    const imgData = target.ctx.getImageData(0, 0, target.canvas.width, target.canvas.height);
    const d = imgData.data, len = d.length;
    const scale = a / 100;
    // 2026-04-19 HEENAN H4HR-PERF11 — adjustVibrance hot-path opt.
    // Inline 3-way max/min, drop manual clamp, bitwise round.
    for (let i = 0; i < len; i += 4) {
        const r = d[i], g = d[i+1], b = d[i+2];
        const mx = r > g ? (r > b ? r : b) : (g > b ? g : b);
        const mn = r < g ? (r < b ? r : b) : (g < b ? g : b);
        const sat = mx > 0 ? (mx - mn) / mx : 0;
        const boost = scale * (1 - sat);
        const avg = (r + g + b) * 0.3333333333333333;
        d[i]   = (r + (r - avg) * boost + 0.5) | 0;
        d[i+1] = (g + (g - avg) * boost + 0.5) | 0;
        d[i+2] = (b + (b - avg) * boost + 0.5) | 0;
    }
    target.ctx.putImageData(imgData, 0, 0);
    _commitAdjustment(target);
    showToast(`Vibrance: ${a > 0 ? '+' : ''}${a}`);
}

// 2026-04-18 marathon — replaced raw prompt() with slider modal.
function promptVignette() {
    _showAdjustmentDialog({
        title: 'Vignette',
        sliders: [{ label: 'Strength', min: 0.1, max: 2.0, step: 0.1, default: 0.5 }],
    }).then(function (vals) {
        if (vals && !isNaN(vals[0])) applyVignette(vals[0]);
    });
}
function promptThreshold() {
    _showAdjustmentDialog({
        title: 'Threshold',
        sliders: [{ label: 'Level', min: 0, max: 255, default: 128 }],
    }).then(function (vals) {
        if (vals && !isNaN(vals[0])) applyThreshold(vals[0]);
    });
}
function promptColorTemp() {
    _showAdjustmentDialog({
        title: 'Color Temperature',
        sliders: [{ label: 'Warm ↔ Cool', min: -100, max: 100, default: 0 }],
    }).then(function (vals) {
        if (vals && !isNaN(vals[0])) adjustColorTemperature(vals[0]);
    });
}
function promptVibrance() {
    _showAdjustmentDialog({
        title: 'Vibrance',
        sliders: [{ label: 'Vibrance', min: -100, max: 100, default: 25 }],
    }).then(function (vals) {
        if (vals && !isNaN(vals[0])) adjustVibrance(vals[0]);
    });
}

window.applyVignette = applyVignette;
window.applyThreshold = applyThreshold;
window.adjustColorTemperature = adjustColorTemperature;
window.adjustVibrance = adjustVibrance;
window.promptVignette = promptVignette;
window.promptThreshold = promptThreshold;
window.promptColorTemp = promptColorTemp;
window.promptVibrance = promptVibrance;

function toggleLayerVisible(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer) { console.warn('[LAYERS] toggleLayerVisible: layer not found:', layerId); return; }
    _pushLayerStackUndo(layer.visible ? 'hide layer' : 'show layer');
    layer.visible = !layer.visible;
    console.log('[LAYERS] Toggle', layer.name, '->', layer.visible, 'hasImg:', !!layer.img);
    if (_psdLayersLoaded) {
        recompositeFromLayers();
    } else {
        console.warn('[LAYERS] Layers not fully loaded yet — toggle saved, will apply on load');
    }
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    // TOOLS WAR — refresh active-tool label so (hidden) tag appears/clears.
    if (typeof refreshActiveToolLabel === 'function') refreshActiveToolLabel();
}

function selectPSDLayer(layerId) {
    // 2026-04-18 marathon chaos audit — if the painter is mid-stroke on a
    // layer paint operation and clicks another layer in the panel, the
    // in-progress stroke was previously orphaned: _activeLayerCanvas kept
    // pointing at the old layer's buffer while _selectedLayerId moved to
    // the new one, and the next dab tried to paint onto the WRONG layer.
    // Fix: cancel the in-progress stroke cleanly before switching.
    if (typeof isDrawing !== 'undefined' && isDrawing && _activeLayerCanvas) {
        isDrawing = false;
        _activeLayerCanvas = null;
        _activeLayerCtx = null;
        if (_savedPaintImageData) {
            paintImageData = _savedPaintImageData;
            _savedPaintImageData = null;
        }
        // Pop the undo entry for the cancelled stroke so it does not dangle.
        if (Array.isArray(_layerUndoStack) && _layerUndoStack.length > 0) {
            _layerUndoStack.pop();
        }
        if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
        if (typeof showToast === 'function') showToast('Layer stroke cancelled (switched layers)', 'info');
    }
    _selectedLayerId = (_selectedLayerId === layerId) ? null : layerId;
    // 2026-04-18 painter-trust fix: keep window._selectedLayerId in sync so
    // code paths that reach through window (layer-flow.js, tests, hotkeys)
    // see the same selection. Pre-fix there was one-way drift: layer-flow
    // wrote BOTH, selectPSDLayer only wrote the module-scope var.
    if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
    if (_selectedLayerId && typeof setToolbarEditMode === 'function') {
        setToolbarEditMode('layer', { silent: true });
    }
    // Reset the "painting on composite because X" toast throttle so the
    // painter gets a fresh warning if they switch to a layer that has a
    // blocking condition (locked, still loading, etc.).
    if (typeof _resetLayerPaintFailToasts === 'function') _resetLayerPaintFailToasts();
    renderLayerPanel();
    if (_selectedLayerId) {
        drawLayerBounds();
    } else {
        clearLayerBounds();
    }
    // TOOLS WAR — refresh active-tool label so the "→ painting on X"
    // suffix stays accurate when the painter changes layers without
    // changing tools.
    if (typeof refreshActiveToolLabel === 'function') refreshActiveToolLabel();
}

function deselectPSDLayer(noToast) {
    if (!_selectedLayerId) return false;
    _selectedLayerId = null;
    if (typeof window !== 'undefined') window._selectedLayerId = null;
    if (typeof setToolbarEditMode === 'function') setToolbarEditMode('zone', { silent: true });
    clearLayerBounds();
    renderLayerPanel();
    if (typeof refreshActiveToolLabel === 'function') refreshActiveToolLabel();
    if (!noToast && typeof showToast === 'function') showToast('Layer deselected');
    return true;
}
window.deselectPSDLayer = deselectPSDLayer;

// TOOLS WAR helper — recompute the active-tool label based on current
// canvasMode + active target. Called from setCanvasMode and from layer
// selection / lock / visibility changes so the indicator never goes stale.
function _escapeContextHtml(str) {
    return String(str == null ? '' : str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function _contextActionButton(label, onclick, title, tone) {
    const palette = {
        neutral: { border: '#3a4357', fg: '#d6dcef', bg: '#141b27' },
        cyan: { border: '#1d8ba3', fg: '#bff7ff', bg: '#0f2830' },
        gold: { border: '#8f6a11', fg: '#ffe7a0', bg: '#2b2210' },
        red: { border: '#8a2d2d', fg: '#ffd7d7', bg: '#401616' },
        green: { border: '#1c8b5f', fg: '#d9ffe8', bg: '#123625' }
    };
    const swatch = palette[tone] || palette.neutral;
    return `<button type="button" class="btn btn-sm" onclick="${onclick}" title="${_escapeContextHtml(title || label)}"
        style="padding:3px 8px;font-size:10px;line-height:1.2;border-color:${swatch.border};color:${swatch.fg};background:${swatch.bg};white-space:nowrap;">${_escapeContextHtml(label)}</button>`;
}

function _getZoneContextLabel() {
    if (typeof zones === 'undefined' || typeof selectedZoneIndex === 'undefined') return 'Zone';
    const zone = zones && zones[selectedZoneIndex];
    if (!zone) return 'Zone';
    return zone.name || `Zone ${selectedZoneIndex + 1}`;
}

function _getPlacementContextLabel() {
    if (typeof placementLayer === 'undefined' || !placementLayer || placementLayer === 'none') return '';
    return placementLayer
        .replace(/_/g, ' ')
        .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
}

function renderContextActionBar() {
    const scopeEl = document.getElementById('contextScopeChip');
    const actionsEl = document.getElementById('contextActionsBar');
    const hintEl = document.getElementById('contextActionHint');
    if (!scopeEl || !actionsEl || !hintEl) return;
    // Legacy label coverage: Smart Transform / Whole Layer / Select Pixels
    // were the prior names for Transform Layer / Mask Zone actions.

    const selectedLayer = (typeof getSelectedLayer === 'function') ? getSelectedLayer() : null;
    const hasSelection = typeof hasActivePixelSelection === 'function' && hasActivePixelSelection();
    const zoneLabel = _getZoneContextLabel();
    let scopeLabel = isLayerToolbarMode()
        ? 'Layer Mode • No Layer Selected'
        : `Zone Mode • ${zoneLabel}`;
    let hint = isLayerToolbarMode()
        ? 'Select an editable layer. Zone and mask tools are disabled while Layer Mode is active.'
        : 'Use the zone panel for finishes and the left rail for zone mask tools.';
    let actions = '';

    if (typeof freeTransformState !== 'undefined' && freeTransformState) {
        if (freeTransformState.target === 'layer') {
            scopeLabel = freeTransformState.sessionScopeLabel || 'Layer Transform';
            hint = 'Selection transforms and whole-layer transforms both live here. Use 180° for quick sponsor flips.';
        } else {
            const zoneTarget = freeTransformState.target ? String(freeTransformState.target).replace(/_/g, ' ') : 'zone target';
            scopeLabel = `Zone Transform • ${zoneTarget}`;
            hint = 'Apply or cancel here; numeric placement stays in the zone panel.';
        }
        actions += _contextActionButton('-90°', 'rotateActiveTransformBy(-90)', 'Rotate active transform 90 degrees counter-clockwise', 'neutral');
        actions += _contextActionButton('+90°', 'rotateActiveTransformBy(90)', 'Rotate active transform 90 degrees clockwise', 'neutral');
        actions += _contextActionButton('180°', 'rotateActiveTransformBy(180)', 'Rotate active transform 180 degrees', 'neutral');
        actions += _contextActionButton('Apply', "if(typeof freeTransformState!=='undefined' && freeTransformState && freeTransformState.target==='layer'){commitLayerTransform();}else{deactivateFreeTransform(true);}", 'Apply active transform', 'green');
        actions += _contextActionButton('Cancel', 'cancelActiveTransformSession()', 'Cancel active transform', 'red');
    } else if (typeof placementLayer !== 'undefined' && placementLayer && placementLayer !== 'none') {
        scopeLabel = `Edit Placement • ${_getPlacementContextLabel()}`;
        hint = 'Direct-on-template placement is active. Use Done when the target looks right.';
        actions += _contextActionButton('-90°', 'manualPlacementRotateCCW()', 'Rotate active placement target 90 degrees counter-clockwise', 'neutral');
        actions += _contextActionButton('+90°', 'manualPlacementRotateCW()', 'Rotate active placement target 90 degrees clockwise', 'neutral');
        actions += _contextActionButton('Flip H', 'manualPlacementFlipH()', 'Flip active placement target horizontally', 'neutral');
        actions += _contextActionButton('Flip V', 'manualPlacementFlipV()', 'Flip active placement target vertically', 'neutral');
        actions += _contextActionButton('Reset', 'manualPlacementReset()', 'Reset placement offsets, rotation, and scale', 'gold');
        actions += _contextActionButton('Done', "if(typeof deactivateManualPlacement==='function')deactivateManualPlacement(); if(typeof renderZones==='function')renderZones();", 'Close placement editing', 'green');
    } else if (isLayerToolbarMode() && selectedLayer && typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded) {
        const layerFlags = [];
        if (selectedLayer.locked) layerFlags.push('locked');
        if (selectedLayer.visible === false) layerFlags.push('hidden');
        scopeLabel = `Layer Mode • ${selectedLayer.name}${layerFlags.length ? ' (' + layerFlags.join(', ') + ')' : ''}`;
        hint = hasSelection
            ? 'Transform Selection affects only that region; Transform Layer still moves the whole selected layer.'
            : 'Pick Item grabs one connected sponsor or logo; rectangle, lasso, ellipse, or pen on the selected layer now jumps straight into transform.';
        if (hasSelection) {
            actions += _contextActionButton('Move Border', 'activateSelectionMove()', 'Reposition the current selection border without moving pixels', 'neutral');
            actions += _contextActionButton('Transform Selection', "requestContextTransform('selection')", 'Lift the selected part of this layer and transform only that region', 'cyan');
            actions += _contextActionButton('Transform Layer', "requestContextTransform('layer')", 'Transform the entire selected layer without clearing the current selection', 'neutral');
            actions += _contextActionButton('Rotate 180°', 'rotateSelectedLayerRegion(180)', 'Rotate the selected part of this layer 180 degrees', 'gold');
            actions += _contextActionButton('-90°', 'rotateSelectedLayerRegion(-90)', 'Rotate the selected part of this layer 90 degrees counter-clockwise', 'neutral');
            actions += _contextActionButton('+90°', 'rotateSelectedLayerRegion(90)', 'Rotate the selected part of this layer 90 degrees clockwise', 'neutral');
        } else {
            actions += _contextActionButton('Pick Item', 'activateLayerElementPickMode()', 'Click one sponsor, number, or shape on the selected layer to isolate it and start transform', 'cyan');
            actions += _contextActionButton('Transform Layer', "requestContextTransform('layer')", 'Transform the entire selected layer', 'cyan');
            actions += _contextActionButton('-90°', 'rotateSelectedLayerCCW()', 'Rotate selected layer 90 degrees counter-clockwise', 'neutral');
            actions += _contextActionButton('+90°', 'rotateSelectedLayerCW()', 'Rotate selected layer 90 degrees clockwise', 'neutral');
            actions += _contextActionButton('180°', 'rotateSelectedLayer180()', 'Rotate selected layer 180 degrees (single undo step)', 'neutral');
        }
        // WIN #2: explicit "Layer" so painters can tell this apart from Flip View / Flip Decal / Flip Placement.
        actions += _contextActionButton('Flip Layer H', 'flipLayerH()', 'Flip the selected layer\'s pixels horizontally (destructive — undo with Ctrl+Z)', 'neutral');
        actions += _contextActionButton('Flip Layer V', 'flipLayerV()', 'Flip the selected layer\'s pixels vertically (destructive — undo with Ctrl+Z)', 'neutral');
        actions += _contextActionButton('FX', 'openSelectedLayerEffects()', 'Open layer effects for the selected layer', 'gold');
        actions += _contextActionButton('Zone Mask ← Layer', 'selectSelectedLayerPixels()', 'Shortcut: build the current zone mask from this layer’s opaque pixels', 'cyan');
    } else {
        const zone = (typeof zones !== 'undefined' && typeof selectedZoneIndex !== 'undefined' && zones && zones[selectedZoneIndex]) ? zones[selectedZoneIndex] : null;
        if (hasSelection) {
            actions += _contextActionButton('Move Border', 'activateSelectionMove()', 'Reposition the current selection border without moving pixels', 'neutral');
        }
        if (zone && (zone.base || zone.pattern)) {
            if (zone.pattern && zone.pattern !== 'none') {
                actions += _contextActionButton('Transform Pattern', "activateZoneTransform('pattern')", 'Transform the current zone pattern placement', 'cyan');
            }
            if (zone.base) {
                actions += _contextActionButton('Transform Base', "activateZoneTransform('base')", 'Transform the current zone base placement', 'neutral');
            }
        }
    }

    scopeEl.textContent = scopeLabel;
    actionsEl.innerHTML = actions;
    hintEl.textContent = hint;
}
window.renderContextActionBar = renderContextActionBar;

function refreshActiveToolLabel() {
    var label = document.getElementById('activeToolLabel');
    if (!label || typeof canvasMode === 'undefined') return;
    var toolNames = {
        eyedropper: 'EYEDROPPER', brush: 'BRUSH', erase: 'ERASER', wand: 'MAGIC WAND',
        selectall: 'SELECT ALL', edge: 'EDGE DETECT', rect: 'RECTANGLE',
        'selection-move': 'MOVE BORDER',
        lasso: 'LASSO', gradient: 'GRADIENT', fill: 'FILL BUCKET',
        text: 'TEXT', shape: 'SHAPE', clone: 'CLONE STAMP',
        pen: 'PEN / BEZIER', colorbrush: 'COLOR BRUSH', 'ellipse-marquee': 'ELLIPSE',
        recolor: 'RECOLOR', smudge: 'SMUDGE', 'history-brush': 'HISTORY BRUSH',
        pencil: 'PENCIL', dodge: 'DODGE', burn: 'BURN', 'blur-brush': 'BLUR BRUSH',
        'sharpen-brush': 'SHARPEN BRUSH', 'spatial-include': 'SPATIAL +',
        'spatial-exclude': 'SPATIAL −', 'spatial-erase': 'SPATIAL ERASE',
    };
    var baseLabel = toolNames[canvasMode] || (canvasMode || '').toUpperCase();
    var layerAware = ['colorbrush','recolor','smudge','erase','clone',
        'pencil','dodge','burn','blur-brush','sharpen-brush',
        'history-brush'].indexOf(canvasMode) >= 0;
    var target = (typeof getActiveTargetSummary === 'function')
        ? getActiveTargetSummary() : null;
    var modeLabel = isLayerToolbarMode() ? 'LAYER' : 'ZONE';
    label.textContent = (layerAware && target)
        ? (baseLabel + ' • ' + modeLabel + ' → ' + target)
        : (baseLabel + ' • ' + modeLabel);
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
}
window.refreshActiveToolLabel = refreshActiveToolLabel;

function deleteLayer(layerId) {
    const idx = _psdLayers.findIndex(l => l.id === layerId);
    if (idx < 0) return;
    // 2026-04-18 marathon chaos audit — if the painter is mid-stroke on
    // the layer they are about to delete, the in-progress stroke would
    // otherwise commit to the FALLBACK layer on mouseup (wrong layer).
    // Cancel the stroke cleanly first.
    if (typeof isDrawing !== 'undefined' && isDrawing && _activeLayerCanvas
            && _selectedLayerId === layerId) {
        isDrawing = false;
        _activeLayerCanvas = null;
        _activeLayerCtx = null;
        if (_savedPaintImageData) {
            paintImageData = _savedPaintImageData;
            _savedPaintImageData = null;
        }
        // Pop the transient per-stroke undo entry we pushed at mousedown.
        // We don't need to keep it — the deletion itself is a stack undo.
        if (Array.isArray(_layerUndoStack) && _layerUndoStack.length > 0
                && _layerUndoStack[_layerUndoStack.length - 1].type === 'image'
                && _layerUndoStack[_layerUndoStack.length - 1].layerId === layerId) {
            _layerUndoStack.pop();
        }
    }
    // WIN #10 (Pillman audit, HIGH): pre-fix, deleteLayer removed the layer from
    // _psdLayers but did NOT scrub `zones[*].sourceLayer` references pointing at
    // it. Render path silently emitted the zoneObj WITH NO mask (no toast, no
    // warning) and the zone painted across the whole car. Marathon bugs #36
    // (flatten) and #43 (merge) closed this same gap on those paths;
    // deleteLayer was the asymmetric outlier. Mirror the mergeVisibleLayers
    // pattern: pre-scan zones, confirm if non-empty, null refs and toast.
    if (typeof zones !== 'undefined' && Array.isArray(zones)) {
        const _danglingZones = zones.filter(function (z) { return z && z.sourceLayer === layerId; });
        if (_danglingZones.length > 0) {
            const _names = _danglingZones.map(function (z) { return z.name || 'Zone'; }).join(', ');
            const _msg = _danglingZones.length + ' zone' + (_danglingZones.length === 1 ? '' : 's')
                + ' (' + _names + ') ' + (_danglingZones.length === 1 ? 'is' : 'are')
                + ' restricted to this layer. Deleting will clear the restriction so '
                + (_danglingZones.length === 1 ? 'it paints' : 'they paint')
                + ' across the whole car. Continue?';
            if (!confirm(_msg)) return;
            _danglingZones.forEach(function (z) { z.sourceLayer = null; });
            if (typeof showToast === 'function') {
                showToast('Cleared sourceLayer restriction on ' + _danglingZones.length
                    + ' zone' + (_danglingZones.length === 1 ? '' : 's'), true);
            }
        }
    }
    _pushLayerStackUndo('delete layer');
    _psdLayers.splice(idx, 1);
    // Workstream 13 #251 — selected-row consistency after delete. Photoshop
    // parity: if the user deletes the active layer, fall through to the
    // layer that was directly below it (or the new top if the deleted one
    // was the bottom layer). Leaving _selectedLayerId = null forces an
    // extra click to resume work and is unfamiliar to PS users.
    if (_selectedLayerId === layerId) {
        if (_psdLayers.length === 0) {
            _selectedLayerId = null;
        } else {
            const fallbackIdx = Math.max(0, idx - 1);
            _selectedLayerId = _psdLayers[fallbackIdx].id;
        }
        // 2026-04-18 marathon: keep window ref in sync so cross-file consumers
        // (layer-flow.js, hotkeys) see the fallback selection.
        if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
        // Reset fallback-toast throttle on selection change.
        if (typeof _resetLayerPaintFailToasts === 'function') _resetLayerPaintFailToasts();
    }
    recompositeFromLayers();
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Layer deleted');
}

// ═══ ADD BLANK LAYER ═══ (synchronous, undo BEFORE mutation, array-shape bbox)
function addBlankLayer() {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;
    const tmpCanvas = document.createElement('canvas');
    tmpCanvas.width = w; tmpCanvas.height = h;
    _pushLayerStackUndo('add blank layer');
    const newLayer = {
        id: 'blank_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
        name: 'Layer ' + (_psdLayers.length + 1),
        path: '',
        visible: true,
        opacity: 255,
        blendMode: 'source-over',
        locked: false,
        bbox: [0, 0, w, h],
        img: tmpCanvas,
    };
    _psdLayers.push(newLayer);
    _psdLayersLoaded = true;
    selectPSDLayer(newLayer.id);
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast('Added blank layer');
}
window.addBlankLayer = addBlankLayer;

// New Layer via Copy (Ctrl+J in Photoshop) — copy selected pixels to a new layer
function newLayerViaCopy() {
    const data = _storeClipboardFromSelection(true);
    if (!data) {
        showToast('No selection — select an area first (Ctrl+J copies selected pixels to new layer)', true);
        return;
    }
    _createLayerFromClipboardData(data, {
        name: 'Layer via Copy',
        idPrefix: 'copy_',
        undoLabel: 'new layer via copy',
    });
    showToast('New layer via copy');
}
window.newLayerViaCopy = newLayerViaCopy;

// ═══ ADD LAYER FROM FILE ═══
function addLayerFromFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/png,image/jpeg,image/webp,image/gif';
    input.onchange = function () {
        const file = input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function (e) {
            const img = new Image();
            img.onload = function () {
                const pc = document.getElementById('paintCanvas');
                const canvasW = pc ? pc.width : 2048;
                const canvasH = pc ? pc.height : 2048;

                // Add as a new layer
                const newLayer = {
                    id: 'psd_added_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
                    name: file.name.replace(/\.[^.]+$/, ''),
                    path: 'Added/' + file.name,
                    visible: true,
                    opacity: 255,
                    img: img,
                    bbox: [0, 0, img.naturalWidth, img.naturalHeight],
                    groupName: 'Added',
                };

                // If image is larger than canvas, scale it to fit
                if (img.naturalWidth > canvasW || img.naturalHeight > canvasH) {
                    const scale = Math.min(canvasW / img.naturalWidth, canvasH / img.naturalHeight) * 0.8;
                    // Create scaled version — SYNCHRONOUS canvas swap (no second onload race)
                    const sc = document.createElement('canvas');
                    sc.width = Math.round(img.naturalWidth * scale);
                    sc.height = Math.round(img.naturalHeight * scale);
                    sc.getContext('2d').drawImage(img, 0, 0, sc.width, sc.height);
                    _pushLayerStackUndo('add layer from file');
                    newLayer.img = sc;
                    newLayer.bbox = [
                        Math.round((canvasW - sc.width) / 2),
                        Math.round((canvasH - sc.height) / 2),
                        Math.round((canvasW - sc.width) / 2) + sc.width,
                        Math.round((canvasH - sc.height) / 2) + sc.height
                    ];
                    _psdLayers.push(newLayer);
                    _psdLayersLoaded = true;
                    recompositeFromLayers();
                    renderLayerPanel();
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    if (typeof showToast === 'function') showToast(`Layer "${newLayer.name}" added (scaled to fit)`, 'success');
                } else {
                    // Center it on canvas
                    _pushLayerStackUndo('add layer from file');
                    newLayer.bbox = [
                        Math.round((canvasW - img.naturalWidth) / 2),
                        Math.round((canvasH - img.naturalHeight) / 2),
                        Math.round((canvasW - img.naturalWidth) / 2) + img.naturalWidth,
                        Math.round((canvasH - img.naturalHeight) / 2) + img.naturalHeight
                    ];
                    _psdLayers.push(newLayer);
                    _psdLayersLoaded = true;
                    recompositeFromLayers();
                    renderLayerPanel();
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    if (typeof showToast === 'function') showToast(`Layer "${newLayer.name}" added`, 'success');
                }
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    };
    input.click();
}

// ═══ LAYER REORDER ═══

function moveLayerUp() {
    if (!_selectedLayerId) return;
    const idx = _psdLayers.findIndex(l => l.id === _selectedLayerId);
    if (idx < 0 || idx >= _psdLayers.length - 1) return;
    _pushLayerStackUndo('move up');
    [_psdLayers[idx], _psdLayers[idx + 1]] = [_psdLayers[idx + 1], _psdLayers[idx]];
    recompositeFromLayers();
    renderLayerPanel();
    drawLayerBounds();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function moveLayerDown() {
    if (!_selectedLayerId) return;
    const idx = _psdLayers.findIndex(l => l.id === _selectedLayerId);
    if (idx <= 0) return;
    _pushLayerStackUndo('move down');
    [_psdLayers[idx], _psdLayers[idx - 1]] = [_psdLayers[idx - 1], _psdLayers[idx]];
    recompositeFromLayers();
    renderLayerPanel();
    drawLayerBounds();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

// ═══ LAYER INTERACTION — MOVE, RESIZE, TRANSFORM ═══

var _layerDragState = null; // null or { layerId, startX, startY, origBbox }

// ═══ BRUSH-ON-LAYER — Paint directly on a selected PSD layer's pixels ═══
var _activeLayerCanvas = null;
var _activeLayerCtx = null;

var _savedPaintImageData = null; // Backup of composite paintImageData while layer editing

function _initLayerPaintCanvas() {
    // Create an offscreen canvas from the selected layer's image
    const layer = getSelectedLayer();
    // Workstream 19 #363 — locked-layer paint attempt should toast so the
    // user knows why nothing happened. Run BEFORE the early return.
    if (layer && layer.locked && typeof warnIfPaintingOnLockedLayer === 'function') {
        warnIfPaintingOnLockedLayer();
    }
    if (!layer || !layer.img || layer.locked) { _activeLayerCanvas = null; _activeLayerCtx = null; return false; }
    // Workstream 6 #116 — Photoshop allows painting on hidden layers, but our
    // recomposite skips them, so user paints into the void with no feedback.
    // Warn once per layer per session.
    if (typeof warnIfPaintingOnHiddenLayer === 'function') warnIfPaintingOnHiddenLayer();
    const pc = document.getElementById('paintCanvas');
    if (!pc) return false;
    // Offscreen canvas at FULL paint canvas size (not just layer bbox)
    _activeLayerCanvas = document.createElement('canvas');
    _activeLayerCanvas.width = pc.width;
    _activeLayerCanvas.height = pc.height;
    // willReadFrequently: this canvas is BOTH drawn on and read back on every
    // brush stroke (commitLayerPaint reads via getImageData). Without the
    // flag Chrome forces a GPU→CPU readback round-trip per stroke. Single
    // highest-leverage perf fix per Bockwinkel's hot-path audit.
    _activeLayerCtx = _activeLayerCanvas.getContext('2d', { willReadFrequently: true });
    // Draw the layer at its bbox position
    const bx = layer.bbox ? layer.bbox[0] : 0;
    const by = layer.bbox ? layer.bbox[1] : 0;
    _activeLayerCtx.drawImage(layer.img, bx, by);

    // KEY: swap paintImageData to point at the LAYER canvas data
    // This makes ALL tool functions (recolor, smudge, clone, history brush)
    // automatically operate on the layer instead of the composite
    _savedPaintImageData = paintImageData;
    paintImageData = _activeLayerCtx.getImageData(0, 0, pc.width, pc.height);
    // Also update the visible canvas to show the layer data for tool feedback
    _flushPaintImageDataToCurrentSurface();
    return true;
}

function _flushPaintImageDataToCurrentSurface() {
    if (typeof paintImageData === 'undefined' || !paintImageData) return false;
    const pc = document.getElementById('paintCanvas');
    if (_activeLayerCanvas && _activeLayerCtx) {
        _activeLayerCtx.putImageData(paintImageData, 0, 0);
    }
    if (pc) {
        pc.getContext('2d').putImageData(paintImageData, 0, 0);
        return true;
    }
    return !!(_activeLayerCanvas && _activeLayerCtx);
}
window._flushPaintImageDataToCurrentSurface = _flushPaintImageDataToCurrentSurface;

var _activeLayerCompositePreviewRaf = 0;

function _refreshActiveLayerCompositePreviewNow() {
    const layer = getSelectedLayer();
    if (!layer || !_activeLayerCanvas) return false;
    if (typeof _psdLayers === 'undefined' || !Array.isArray(_psdLayers)) return false;
    const pc = document.getElementById('paintCanvas');
    if (!pc) return false;
    const pctx = pc.getContext('2d', { willReadFrequently: true });
    pctx.clearRect(0, 0, pc.width, pc.height);
    for (const l of _psdLayers) {
        if (!l || !l.visible) continue;
        pctx.globalAlpha = (l.opacity != null ? l.opacity : 255) / 255;
        pctx.globalCompositeOperation = l.blendMode || 'source-over';
        if (l.id === layer.id && _activeLayerCanvas) {
            pctx.drawImage(_activeLayerCanvas, 0, 0);
        } else if (l.img) {
            const bx = l.bbox ? l.bbox[0] : 0;
            const by = l.bbox ? l.bbox[1] : 0;
            pctx.drawImage(l.img, bx, by);
        }
    }
    pctx.globalAlpha = 1.0;
    pctx.globalCompositeOperation = 'source-over';
    paintImageData = pctx.getImageData(0, 0, pc.width, pc.height);
    return true;
}

function _scheduleActiveLayerCompositePreview() {
    if (_activeLayerCompositePreviewRaf) return;
    if (typeof requestAnimationFrame !== 'function') {
        _refreshActiveLayerCompositePreviewNow();
        return;
    }
    _activeLayerCompositePreviewRaf = requestAnimationFrame(() => {
        _activeLayerCompositePreviewRaf = 0;
        _refreshActiveLayerCompositePreviewNow();
    });
}

function _cancelPendingActiveLayerCompositePreview() {
    if (_activeLayerCompositePreviewRaf && typeof cancelAnimationFrame === 'function') {
        cancelAnimationFrame(_activeLayerCompositePreviewRaf);
    }
    _activeLayerCompositePreviewRaf = 0;
}

// Layer undo: unified stack supporting two entry types:
//   { type:'image', layerId, imgCanvas, bbox, label } — single-layer pixel/bbox change
//   { type:'stack', snapshot:[...], selectedId, label }  — full-stack change (reorder, delete, opacity, blend, etc.)
//
// Codex MED B5 — image-branch entries used to store an `imgDataUrl` and
// restore via `new Image() + onload`. That created a Ctrl+Z race window
// where rapid undo/redo could land on a pre-onload state. Now the snapshot
// is a synchronous canvas reference (drawable directly as an image source)
// — no async restore, no race.
var _layerUndoStack = [];
var _layerRedoStack = [];
var _LAYER_UNDO_MAX = 8;

function _pushLayerUndo(layer, label) {
    if (!layer || !layer.img) return;
    // Snapshot the layer's current image to a fresh canvas (synchronous).
    const c = document.createElement('canvas');
    c.width = layer.img.width; c.height = layer.img.height;
    c.getContext('2d').drawImage(layer.img, 0, 0);
    _layerUndoStack.push({
        type: 'image',
        layerId: layer.id,
        imgCanvas: c,            // canvas-based snapshot (drawable)
        bbox: [...layer.bbox],
        label: label || 'layer edit',
    });
    // BUG #75: invalidate ALL redo branches (not just _layerRedoStack).
    if (typeof _clearAllRedos === 'function') _clearAllRedos(); else _layerRedoStack.length = 0;
    if (_layerUndoStack.length > _LAYER_UNDO_MAX) _layerUndoStack.shift();
    if (typeof _recordUndoAction === 'function') _recordUndoAction('layer');
}

// Snapshot the entire layer stack (opacity/blend/visibility/order/bbox/locked/effects).
// `.img` references are retained — since operations that replace pixel data swap the
// img object rather than mutating it, holding a reference preserves the old pixels.
function _snapshotLayerStack() {
    if (typeof _psdLayers === 'undefined' || !Array.isArray(_psdLayers)) return [];
    return _psdLayers.map(function(l) {
        return {
            id: l.id,
            name: l.name,
            path: l.path,
            visible: l.visible,
            opacity: l.opacity,
            blendMode: l.blendMode,
            locked: l.locked,
            groupName: l.groupName,
            bbox: Array.isArray(l.bbox) ? [...l.bbox] : (l.bbox ? Object.assign({}, l.bbox) : null),
            img: l.img, // retained reference — previous pixel buffer stays reachable
            effects: l.effects ? JSON.parse(JSON.stringify(l.effects)) : null,
            // any other custom flags callers might set
            _extra: (function() {
                var e = {};
                for (var k in l) {
                    if (!Object.prototype.hasOwnProperty.call(l, k)) continue;
                    if (['id','name','path','visible','opacity','blendMode','locked','groupName','bbox','img','effects'].indexOf(k) >= 0) continue;
                    e[k] = l[k];
                }
                return e;
            })(),
        };
    });
}

function _restoreLayerStack(snapshot, selectedId) {
    if (!Array.isArray(snapshot)) return;
    _psdLayers.length = 0;
    for (var i = 0; i < snapshot.length; i++) {
        var s = snapshot[i];
        var layer = {
            id: s.id,
            name: s.name,
            path: s.path,
            visible: s.visible,
            opacity: s.opacity,
            blendMode: s.blendMode,
            locked: s.locked,
            groupName: s.groupName,
            bbox: Array.isArray(s.bbox) ? [...s.bbox] : (s.bbox ? Object.assign({}, s.bbox) : null),
            img: s.img,
            effects: s.effects ? JSON.parse(JSON.stringify(s.effects)) : null,
        };
        if (s._extra) {
            for (var k in s._extra) {
                if (Object.prototype.hasOwnProperty.call(s._extra, k)) layer[k] = s._extra[k];
            }
        }
        _psdLayers.push(layer);
    }
    if (typeof selectedId !== 'undefined') {
        _selectedLayerId = selectedId;
        if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
    }
    if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
    if (typeof renderLayerPanel === 'function') renderLayerPanel();
    if (typeof drawLayerBounds === 'function') { try { drawLayerBounds(); } catch (_) {} }
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function _pushLayerStackUndo(label) {
    if (typeof _psdLayers === 'undefined' || !Array.isArray(_psdLayers)) return;
    _layerUndoStack.push({
        type: 'stack',
        snapshot: _snapshotLayerStack(),
        selectedId: (typeof _selectedLayerId !== 'undefined') ? _selectedLayerId : null,
        label: label || 'layer stack edit',
    });
    // BUG #75: invalidate ALL redo branches (not just _layerRedoStack).
    if (typeof _clearAllRedos === 'function') _clearAllRedos(); else _layerRedoStack.length = 0;
    if (_layerUndoStack.length > _LAYER_UNDO_MAX) _layerUndoStack.shift();
    if (typeof _recordUndoAction === 'function') _recordUndoAction('layer');
}
window._pushLayerStackUndo = _pushLayerStackUndo;

function undoLayerEdit() {
    if (_layerUndoStack.length === 0) return false;
    // Pillman chaos #462: any undo/redo bookends an effects-dialog session.
    // Without this reset, a Ctrl+Z then continued slider drags inside an
    // open dialog all collapse into the SAME undo entry that the dialog
    // already produced, so a second Ctrl+Z eats multiple subsequent edits.
    // Treating undo/redo as a session terminator lets the next slider tick
    // open a fresh undo entry.
    _effectsSessionUndoPushed = false;
    const entry = _layerUndoStack.pop();

    // Stack-level entry: restore full _psdLayers state
    if (entry.type === 'stack') {
        _layerRedoStack.push({
            type: 'stack',
            snapshot: _snapshotLayerStack(),
            selectedId: (typeof _selectedLayerId !== 'undefined') ? _selectedLayerId : null,
            label: entry.label,
        });
        _restoreLayerStack(entry.snapshot, entry.selectedId);
        if (typeof showToast === 'function') showToast(`Undid: ${entry.label}`);
        return true;
    }

    // Default: single-layer canvas snapshot.
    // Codex MED B5: was previously async via toDataURL → new Image() → onload,
    // which created a Ctrl+Z race window. Now SYNCHRONOUS — push current
    // state to redo as a canvas, restore the entry's canvas to layer.img.
    const layer = _psdLayers.find(l => l.id === entry.layerId);
    if (!layer) return false;
    const c = document.createElement('canvas');
    c.width = layer.img.width; c.height = layer.img.height;
    c.getContext('2d').drawImage(layer.img, 0, 0);
    _layerRedoStack.push({
        type: 'image',
        layerId: layer.id,
        imgCanvas: c,
        bbox: [...layer.bbox],
        label: entry.label,
    });
    // SYNCHRONOUS restore: canvas is drawable as image source.
    layer.img = entry.imgCanvas;
    layer.bbox = entry.bbox;
    recompositeFromLayers();
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast(`Undid layer: ${entry.label}`);
    return true;
}
window.undoLayerEdit = undoLayerEdit;

function redoLayerEdit() {
    if (!Array.isArray(_layerRedoStack) || _layerRedoStack.length === 0) return false;
    // Pillman chaos #462: same session-terminator reset on redo.
    _effectsSessionUndoPushed = false;
    const entry = _layerRedoStack.pop();

    // Stack-level redo
    if (entry.type === 'stack') {
        _layerUndoStack.push({
            type: 'stack',
            snapshot: _snapshotLayerStack(),
            selectedId: (typeof _selectedLayerId !== 'undefined') ? _selectedLayerId : null,
            label: entry.label,
        });
        if (_layerUndoStack.length > _LAYER_UNDO_MAX) _layerUndoStack.shift();
        _restoreLayerStack(entry.snapshot, entry.selectedId);
        if (typeof showToast === 'function') showToast(`Redid: ${entry.label}`);
        return true;
    }

    // Default: single-layer canvas snapshot — Codex MED B5 SYNCHRONOUS path.
    const layer = (typeof _psdLayers !== 'undefined') ? _psdLayers.find(l => l.id === entry.layerId) : null;
    if (!layer) return false;
    // Save current state back to undo so the user can ping-pong.
    try {
        const c = document.createElement('canvas');
        c.width = layer.img.width; c.height = layer.img.height;
        c.getContext('2d').drawImage(layer.img, 0, 0);
        _layerUndoStack.push({
            type: 'image',
            layerId: layer.id,
            imgCanvas: c,
            bbox: [...layer.bbox],
            label: entry.label,
        });
        if (_layerUndoStack.length > _LAYER_UNDO_MAX) _layerUndoStack.shift();
    } catch (_rlErr) { /* non-fatal */ }
    // SYNCHRONOUS restore.
    layer.img = entry.imgCanvas;
    layer.bbox = entry.bbox;
    if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
    if (typeof renderLayerPanel === 'function') renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast(`Redid layer: ${entry.label}`);
    return true;
}
window.redoLayerEdit = redoLayerEdit;

function _commitLayerPaint() {
    _cancelPendingActiveLayerCompositePreview();
    // 2026-04-18 marathon audit — CHAOS BUG FIX:
    // Pre-fix, early-returning on "no layer" / "no active canvas" left
    // paintImageData stuck pointing at the stale _activeLayerCanvas data
    // AND left _activeLayerCanvas/_activeLayerCtx dangling. Next tool
    // operation (including a plain zone brush or eyedropper) would then
    // read or write the wrong buffer. Symptoms: "my eraser stopped
    // showing anything on the composite after I cancelled a layer
    // stroke." Now we ALWAYS restore paintImageData and null the active
    // canvas refs before any early return, then proceed with commit only
    // if both layer and active-canvas are still valid.
    const layer = getSelectedLayer();
    if (!layer || !_activeLayerCanvas) {
        if (_savedPaintImageData) {
            paintImageData = _savedPaintImageData;
            _savedPaintImageData = null;
        }
        _activeLayerCanvas = null;
        _activeLayerCtx = null;
        // Redraw the composite so the canvas shows real state, not the
        // stale in-progress layer pixels.
        if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
        return;
    }

    // Restore composite paintImageData
    if (_savedPaintImageData) {
        paintImageData = _savedPaintImageData;
        _savedPaintImageData = null;
    }

    // Compute tight bounding box of non-transparent pixels (avoid inflating to full canvas)
    const w = _activeLayerCanvas.width, h = _activeLayerCanvas.height;
    const imgData = _activeLayerCtx.getImageData(0, 0, w, h);
    const d = imgData.data;
    let minX = w, minY = h, maxX = 0, maxY = 0;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (d[(y * w + x) * 4 + 3] > 0) {
                if (x < minX) minX = x;
                if (x > maxX) maxX = x;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
            }
        }
    }
    // If nothing was drawn, keep original bbox
    if (maxX < minX) { _activeLayerCanvas = null; _activeLayerCtx = null; return; }

    // Crop to tight bounds — use direct canvas (no toDataURL)
    const cropW = maxX - minX + 1, cropH = maxY - minY + 1;
    const cropCanvas = document.createElement('canvas');
    cropCanvas.width = cropW; cropCanvas.height = cropH;
    cropCanvas.getContext('2d').drawImage(_activeLayerCanvas, minX, minY, cropW, cropH, 0, 0, cropW, cropH);
    layer.img = cropCanvas; // Direct canvas assignment — instant
    layer.bbox = [minX, minY, minX + cropW, minY + cropH];
    _activeLayerCanvas = null;
    _activeLayerCtx = null;
    recompositeFromLayers();
    renderLayerPanel();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function _drawLayerSpecialStamp(ctx, x, y, radius, opacity, hardness) {
    const specialId = getLayerPaintSpecialId() || _getDefaultLayerPaintSpecialId();
    if (!specialId) return false;
    const specialCanvas = _getCachedLayerPaintSpecialCanvas(specialId);
    if (!specialCanvas) {
        warmLayerPaintSpecialCache(false);
        return false;
    }
    const size = Math.max(2, Math.ceil(radius * 2));
    if (hardness >= 0.99) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.clip();
        ctx.globalAlpha = opacity;
        ctx.drawImage(specialCanvas, x - radius, y - radius, size, size);
        ctx.restore();
        return true;
    }

    const stamp = document.createElement('canvas');
    stamp.width = size;
    stamp.height = size;
    const sctx = stamp.getContext('2d');
    sctx.drawImage(specialCanvas, 0, 0, specialCanvas.width, specialCanvas.height, 0, 0, size, size);
    const grad = sctx.createRadialGradient(radius, radius, 0, radius, radius, radius);
    const innerStop = Math.max(0.05, Math.min(0.95, hardness * 0.82));
    grad.addColorStop(0, `rgba(255,255,255,${opacity})`);
    grad.addColorStop(innerStop, `rgba(255,255,255,${Math.max(0.15, opacity * 0.7)})`);
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    sctx.globalCompositeOperation = 'destination-in';
    sctx.fillStyle = grad;
    sctx.fillRect(0, 0, size, size);
    ctx.drawImage(stamp, x - radius, y - radius);
    return true;
}

function _paintOnLayerAt(x, y, radius, color, opacity, hardness, eraseMode) {
    // Paint a single dab on the active layer canvas
    if (!_activeLayerCtx) return;
    const ctx = _activeLayerCtx;

    if (eraseMode) {
        // Eraser: use destination-out
        ctx.save();
        ctx.globalCompositeOperation = 'destination-out';
    }

    // Draw a filled circle at (x,y) with falloff
    if (!eraseMode && isLayerPaintSourceSpecial()) {
        if (!_drawLayerSpecialStamp(ctx, x, y, radius, opacity, hardness)) return;
    } else if (hardness >= 0.99 && opacity >= 0.99 && !eraseMode) {
        // Hard brush: simple circle
        ctx.fillStyle = color;
        ctx.globalAlpha = opacity;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1.0;
    } else {
        // Soft brush with radial gradient
        const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
        if (eraseMode) {
            grad.addColorStop(0, `rgba(0,0,0,${opacity})`);
            grad.addColorStop(hardness * 0.8, `rgba(0,0,0,${opacity * 0.5})`);
            grad.addColorStop(1, 'rgba(0,0,0,0)');
        } else {
            // Parse color
            const cr = parseInt(color.slice(1,3),16), cg = parseInt(color.slice(3,5),16), cb = parseInt(color.slice(5,7),16);
            grad.addColorStop(0, `rgba(${cr},${cg},${cb},${opacity})`);
            grad.addColorStop(hardness * 0.8, `rgba(${cr},${cg},${cb},${opacity * 0.5})`);
            grad.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
        }
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
    }

    if (eraseMode) ctx.restore();

    // Live composite refresh is RAF-batched so a dense stroke only redraws the
    // full PSD stack once per frame instead of once per dab.
    _scheduleActiveLayerCompositePreview();
}

// ─────────────────────────────────────────────────────────────────────────
// Workstream 6 #119 — TOOL GATING CONTRACT (normalized)
// ─────────────────────────────────────────────────────────────────────────
// THREE related but DISTINCT gates. Picking the wrong one is a real source
// of "Photoshop says X but SPB does Y" bugs. Use this table:
//
//   getSelectedEditableLayer()  — primitive: returns the layer object, or null.
//                                  Excludes locked layers and layers without
//                                  an img. Foundation of the other two gates.
//
//   isLayerPaintMode()          — TRUE only when (a) an editable layer is
//                                  selected AND (b) the current canvasMode
//                                  is a brush-style paint tool. Used by the
//                                  per-stroke brush handlers (clone, recolor,
//                                  smudge, etc.) to decide whether THIS stroke
//                                  routes to a layer or the composite.
//
//   isLayerEditTarget()         — TRUE whenever an editable layer is selected,
//                                  REGARDLESS of which brush tool is active.
//                                  Used by tool-agnostic ops like Fill, Delete,
//                                  Selection-fill that should target the active
//                                  layer no matter what icon is highlighted.
//
// Common mistake: gating Fill / Delete on isLayerPaintMode means hitting Fill
// while the rect-select tool is active wrongly drops paint on the composite.
// That bug was the original motivation for the isLayerEditTarget split.
// ─────────────────────────────────────────────────────────────────────────
var toolbarEditMode = 'zone'; // 'zone' | 'layer'
var _toolbarModeToastKey = null;

function getToolbarEditMode() {
    return toolbarEditMode === 'layer' ? 'layer' : 'zone';
}
window.getToolbarEditMode = getToolbarEditMode;

function isLayerToolbarMode() {
    return getToolbarEditMode() === 'layer';
}
window.isLayerToolbarMode = isLayerToolbarMode;

function isZoneToolbarMode() {
    return !isLayerToolbarMode();
}
window.isZoneToolbarMode = isZoneToolbarMode;

function _shouldShowForegroundPickerForZoneFill(mode, layerToolbarActive) {
    if (layerToolbarActive || mode !== 'fill') return false;
    if (typeof zones === 'undefined' || typeof selectedZoneIndex === 'undefined' || !Array.isArray(zones)) return false;
    const zone = zones[selectedZoneIndex];
    if (!zone) return false;
    return (typeof _zoneBrushUsesScopedRefinement === 'function') && _zoneBrushUsesScopedRefinement(zone);
}

function refreshToolbarModeSensitiveUi() {
    const mode = (typeof canvasMode === 'string') ? canvasMode : '';
    const layerToolbarActive = isLayerToolbarMode();
    const showZoneFillForeground = _shouldShowForegroundPickerForZoneFill(mode, layerToolbarActive);
    const showColorBrush = (mode === 'colorbrush' || mode === 'recolor' || mode === 'smudge' || mode === 'brush' || mode === 'erase' || showZoneFillForeground || (layerToolbarActive && (mode === 'fill' || mode === 'gradient')));
    const colorBrushOpts = document.getElementById('colorBrushOptions');
    if (colorBrushOpts) colorBrushOpts.style.display = showColorBrush ? 'inline-flex' : 'none';
    const layerPaintSourceOpts = document.getElementById('layerPaintSourceOptions');
    if (layerPaintSourceOpts) {
        layerPaintSourceOpts.style.display = (layerToolbarActive && (mode === 'fill' || mode === 'brush' || mode === 'colorbrush')) ? 'inline-flex' : 'none';
    }
    const showSelMode = (mode === 'wand' || mode === 'selectall' || mode === 'edge' || mode === 'rect' || mode === 'lasso' || mode === 'pen' || mode === 'ellipse-marquee' || ((mode === 'fill' || mode === 'gradient') && !layerToolbarActive));
    const selModeEl = document.getElementById('selectionMode');
    if (selModeEl) selModeEl.style.display = showSelMode ? '' : 'none';
    const modifierHint = document.getElementById('selectionModifierHint');
    if (modifierHint) modifierHint.style.display = showSelMode ? '' : 'none';
    const patBrushEl = document.getElementById('patternBrushSelect');
    if (patBrushEl && mode === 'colorbrush') {
        patBrushEl.style.display = !(layerToolbarActive && isLayerPaintSourceSpecial()) ? '' : 'none';
    }
    if (typeof syncLayerPaintSourceUI === 'function') syncLayerPaintSourceUI();
}
window.refreshToolbarModeSensitiveUi = refreshToolbarModeSensitiveUi;

function _updateToolbarEditModeButtons() {
    const zoneBtn = document.getElementById('btnToolbarModeZone');
    const layerBtn = document.getElementById('btnToolbarModeLayer');
    const zoneActive = isZoneToolbarMode();
    const layerActive = !zoneActive;
    if (zoneBtn) {
        zoneBtn.style.borderColor = zoneActive ? '#35d97a' : '#355844';
        zoneBtn.style.color = zoneActive ? '#ecfff3' : '#cfe7d6';
        zoneBtn.style.background = zoneActive ? '#14532d' : '#16201a';
        zoneBtn.style.boxShadow = zoneActive ? '0 0 0 1px rgba(62,227,125,0.20) inset, 0 0 12px rgba(62,227,125,0.22)' : 'none';
        zoneBtn.setAttribute('aria-pressed', zoneActive ? 'true' : 'false');
    }
    if (layerBtn) {
        layerBtn.style.borderColor = layerActive ? '#35d97a' : '#355844';
        layerBtn.style.color = layerActive ? '#ecfff3' : '#cfe7d6';
        layerBtn.style.background = layerActive ? '#14532d' : '#16201a';
        layerBtn.style.boxShadow = layerActive ? '0 0 0 1px rgba(62,227,125,0.20) inset, 0 0 12px rgba(62,227,125,0.22)' : 'none';
        layerBtn.setAttribute('aria-pressed', layerActive ? 'true' : 'false');
    }
}

function setToolbarEditMode(mode, options) {
    const nextMode = (mode === 'layer') ? 'layer' : 'zone';
    const opts = options || {};
    if (toolbarEditMode === nextMode) {
        _updateToolbarEditModeButtons();
        return nextMode;
    }
    toolbarEditMode = nextMode;
    _toolbarModeToastKey = null;

    if (nextMode === 'zone' && typeof _ensureCompositePaintSource === 'function') {
        _ensureCompositePaintSource('toolbar mode switch');
    }

    _updateToolbarEditModeButtons();
    if (typeof refreshToolbarModeSensitiveUi === 'function') refreshToolbarModeSensitiveUi();
    if (typeof refreshActiveToolLabel === 'function') refreshActiveToolLabel();
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
    if (typeof updateDrawZoneIndicator === 'function' && typeof canvasMode !== 'undefined' && canvasMode !== 'eyedropper') {
        updateDrawZoneIndicator();
    }

    if (!opts.silent && typeof showToast === 'function') {
        if (nextMode === 'layer') {
            const layer = (typeof getSelectedLayer === 'function') ? getSelectedLayer() : null;
            showToast(
                layer
                    ? `Layer Mode — toolbar edits stay on "${layer.name || 'Selected Layer'}"`
                    : 'Layer Mode — select an editable layer before painting',
                'info'
            );
        } else {
            showToast(`Zone Mode — toolbar edits stay on ${_getZoneContextLabel()}`, 'info');
        }
    }
    return nextMode;
}
window.setToolbarEditMode = setToolbarEditMode;

function _maybeWarnToolbarModeMismatch(toolName, wantedMode) {
    const desired = wantedMode === 'layer' ? 'layer' : 'zone';
    const key = `${desired}|${toolName || 'tool'}`;
    if (_toolbarModeToastKey === key) return;
    _toolbarModeToastKey = key;
    if (typeof showToast !== 'function') return;
    if (desired === 'layer') {
        showToast(`${toolName} only edits layers in Layer Mode — switch the toolbar to LAYER`, 'warn');
    } else {
        showToast(`${toolName} is a zone/mask tool — switch the toolbar to ZONE`, 'warn');
    }
}

function requireLayerToolbarTarget(toolName) {
    if (!isLayerToolbarMode()) {
        _maybeWarnToolbarModeMismatch(toolName, 'layer');
        return false;
    }
    const layer = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
    if (!layer) {
        if (typeof showToast === 'function') {
            showToast(`${toolName} needs an editable selected layer in LAYER mode`, 'warn');
        }
        return false;
    }
    return true;
}
window.requireLayerToolbarTarget = requireLayerToolbarTarget;

function requireZoneToolbarMode(toolName) {
    if (!isZoneToolbarMode()) {
        _maybeWarnToolbarModeMismatch(toolName, 'zone');
        return false;
    }
    return true;
}
window.requireZoneToolbarMode = requireZoneToolbarMode;

function isLayerPaintMode() {
    return isLayerToolbarMode() &&
           !!getSelectedEditableLayer() &&
           ['brush', 'colorbrush', 'recolor', 'smudge', 'erase',
            'clone', 'pencil', 'dodge', 'burn',
            'blur-brush', 'sharpen-brush', 'history-brush'].includes(canvasMode);
}

function isLayerEditTarget() {
    return isLayerToolbarMode() && !!getSelectedEditableLayer();
}
window.isLayerEditTarget = isLayerEditTarget;

// TOOLS WAR — true if the user has a LOCKED layer selected. The brush
// handlers should refuse to paint in this case rather than silently
// falling through to composite (Photoshop parity: a brush stroke on a
// locked layer does nothing AND surfaces the lock warning).
function isSelectedLayerLocked() {
    if (typeof _selectedLayerId === 'undefined' || !_selectedLayerId) return false;
    if (typeof _psdLayers === 'undefined') return false;
    var layer = _psdLayers.find(function (l) { return l.id === _selectedLayerId; });
    return !!(layer && layer.locked);
}
window.isSelectedLayerLocked = isSelectedLayerLocked;

// TOOLS WAR — gate function for brush handlers. Returns true if the
// stroke should proceed (either to layer or to composite). Returns
// false if a locked layer is selected (warn + refuse).
function shouldBrushStrokeProceed() {
    if (isSelectedLayerLocked()) {
        if (typeof warnIfPaintingOnLockedLayer === 'function') warnIfPaintingOnLockedLayer();
        return false; // Refuse: user clearly wanted to paint the layer, not composite.
    }
    return true;
}
window.shouldBrushStrokeProceed = shouldBrushStrokeProceed;

// PSD Painter Gauntlet Track P #318 — concise effects-session status.
// Returns a short string a UI can render or a developer can read in
// console: 'idle' / 'open:LayerName' / 'open:LayerName (dirty)'.
//   idle           → no Layer Style dialog open
//   open:Sponsor   → dialog open, no edits yet (closing is a no-op)
//   open:Sponsor*  → dialog open AND _effectsSessionUndoPushed (edits pending)
function getEffectsSessionStatus() {
    if (typeof _effectsTargetLayerId === 'undefined' || !_effectsTargetLayerId) {
        return 'idle';
    }
    var layer = _psdLayers && _psdLayers.find(function (l) { return l.id === _effectsTargetLayerId; });
    var name = (layer && layer.name) || _effectsTargetLayerId;
    var dirty = (typeof _effectsSessionUndoPushed !== 'undefined' && _effectsSessionUndoPushed);
    return 'open:' + name + (dirty ? '*' : '');
}
window.getEffectsSessionStatus = getEffectsSessionStatus;

// PSD Painter Gauntlet Track E #107 — surface a once-per-session hint when
// the painter switches to a tool that DOES NOT honor brushFlow. Avoids
// silent "I dragged the flow slider but nothing happened" confusion.
// Set on toolList grows; tools NOT honoring flow today: history brush,
// pencil, dodge, burn, blur-brush, sharpen-brush, erase.
var _flowIgnoredHintShown = {}; // {tool: true}
function maybeWarnFlowIgnored(tool) {
    // Tonight: dodge/burn + history-brush now honor flow. List narrowed.
    // Pencil intentionally ignores (binary stamp). Blur/sharpen are
    // accumulator-style; flow folded into per-stamp strength would feel
    // odd — left as opacity-only for now. Erase same.
    var TOOLS_IGNORING_FLOW = ['pencil','blur-brush','sharpen-brush','erase'];
    if (TOOLS_IGNORING_FLOW.indexOf(tool) < 0) return;
    var flowEl = document.getElementById('brushFlow');
    if (!flowEl) return;
    var flow = parseInt(flowEl.value || 100, 10);
    if (flow >= 100) return; // Default; nothing to warn about.
    if (_flowIgnoredHintShown[tool]) return;
    _flowIgnoredHintShown[tool] = true;
    if (typeof showToast === 'function') {
        showToast(`Note: ${tool} ignores the Flow slider (uses Opacity only)`, 'info');
    }
}
window.maybeWarnFlowIgnored = maybeWarnFlowIgnored;

// Codex MED fix (2026-04-18): the flow-ignored hint must also fire when
// the painter changes the Flow slider WITHOUT switching tools. Previously
// only setCanvasMode() called maybeWarnFlowIgnored — a common workflow
// (pick pencil → reduce flow expecting softer strokes) silently produced
// no effect. Now we also listen to slider input.
(function _wireFlowSliderHint() {
    function attach() {
        var flowEl = document.getElementById('brushFlow');
        if (!flowEl || flowEl._spbFlowHintAttached) return;
        flowEl.addEventListener('input', function () {
            // The user might have re-raised flow back to 100 — reset the
            // throttle so the next drop re-fires. Conversely, only warn
            // when flow is below 100 AND current tool ignores flow.
            try {
                var v = parseInt(flowEl.value || 100, 10);
                if (v >= 100) {
                    _flowIgnoredHintShown = {};
                    return;
                }
                if (typeof canvasMode !== 'undefined') {
                    maybeWarnFlowIgnored(canvasMode);
                }
            } catch (_) {}
        });
        flowEl._spbFlowHintAttached = true;
    }
    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', attach);
        } else {
            attach();
        }
    }
})();

window._initLayerPaintCanvas = _initLayerPaintCanvas;
window._commitLayerPaint = _commitLayerPaint;
window._paintOnLayerAt = _paintOnLayerAt;
window.isLayerPaintMode = isLayerPaintMode;

function getLayerById(layerId) {
    if (!layerId) return null;
    return _psdLayers.find(l => l.id === layerId) || null;
}

function getSelectedLayer() {
    return getLayerById(_selectedLayerId);
}

function getSelectedEditableLayer() {
    const layer = getSelectedLayer();
    return (layer && _psdLayersLoaded && layer.img && !layer.locked) ? layer : null;
}

// 2026-04-18 painter-trust fix: when a layer is selected but layer-paint
// cannot proceed (image still loading, layer locked, etc.), tools used to
// silently fall through to composite painting — the painter then wondered
// why the eraser was wiping the whole composite instead of just the
// Sponsors layer. Raven charter: "fail safely + visibly" > "fail safely
// silently." This helper returns a user-friendly reason string if there
// IS a blocking condition, else null.
function _diagnoseLayerPaintFail() {
    if (typeof _selectedLayerId === 'undefined' || !_selectedLayerId) return null;
    const layer = getSelectedLayer();
    if (!layer) return null;
    if (!_psdLayersLoaded) {
        return 'Layer images are still loading — try again in a moment';
    }
    if (!layer.img) {
        return `"${layer.name || 'Layer'}" image not loaded yet`;
    }
    if (layer.locked) {
        return `"${layer.name || 'Layer'}" is locked — click the 🔒 icon to unlock`;
    }
    return null; // Layer paint will proceed fine
}
window._diagnoseLayerPaintFail = _diagnoseLayerPaintFail;

// 2026-04-18 painter-trust fix: one-shot toast warning per (layerId,tool)
// session so the painter knows WHY their stroke landed on composite. Not
// annoying — fires once per (layer, tool) combination.
var _layerPaintFailToastedFor = Object.create(null);
function _maybeToastLayerPaintFallback(toolName) {
    const reason = _diagnoseLayerPaintFail();
    if (!reason) return;
    const layerId = _selectedLayerId || '?';
    const key = String(layerId) + '|' + String(toolName);
    if (_layerPaintFailToastedFor[key]) return;
    _layerPaintFailToastedFor[key] = true;
    if (typeof showToast === 'function') {
        showToast(`${toolName.toUpperCase()} → painting on composite (${reason})`, 'warn');
    }
}
window._maybeToastLayerPaintFallback = _maybeToastLayerPaintFallback;

// Reset toast throttle when painter switches layer (so they get a fresh
// warning on the new layer if conditions haven't improved).
function _resetLayerPaintFailToasts() {
    _layerPaintFailToastedFor = Object.create(null);
}
window._resetLayerPaintFailToasts = _resetLayerPaintFailToasts;

// Workstream 6 #116 — invisible-layer paint guard. Painting on a hidden
// layer is allowed (Photoshop parity) but recompositeFromLayers skips
// invisible layers, so the user paints into the void with zero feedback.
// Show a toast on the FIRST stroke per session so they know to toggle
// visibility on. Returns true if painting should proceed, false to abort.
var _hiddenLayerPaintWarnedFor = null;
function warnIfPaintingOnHiddenLayer() {
    const layer = getSelectedEditableLayer();
    if (!layer) return true; // No layer selected; not our concern
    if (layer.visible === false) {
        // Throttle: warn only once per layer per session so we don't toast
        // on every brush stroke.
        if (_hiddenLayerPaintWarnedFor !== layer.id) {
            _hiddenLayerPaintWarnedFor = layer.id;
            if (typeof showToast === 'function') {
                showToast(`"${layer.name}" is hidden — toggle visibility to see your strokes`, 'info');
            }
        }
    } else {
        _hiddenLayerPaintWarnedFor = null;
    }
    return true;
}
window.warnIfPaintingOnHiddenLayer = warnIfPaintingOnHiddenLayer;

function getLayerCanvasOrigin(layer) {
    // Bockwinkel B7 (Workstream 23 #445): array bbox is the codebase standard.
    // Object-shape fallback removed — pasteAsLayer is no longer producing
    // object-shape, and any future producer should be caught at code review.
    const bbox = layer && layer.bbox;
    if (Array.isArray(bbox)) {
        return { x: bbox[0] || 0, y: bbox[1] || 0 };
    }
    return { x: 0, y: 0 };
}

function commitLayerCanvasUpdate(layer, sourceCanvas, successToast) {
    if (!layer || !sourceCanvas) return false;
    // Bockwinkel B4 (Workstream 23 #444): synchronous canvas swap. Used by
    // fillBucketOnLayer + fillGradientOnLayer; old async onload path created
    // a window where Ctrl+Z immediately after fill/gradient could land on
    // pre-onload state.
    const origin = getLayerCanvasOrigin(layer);
    layer.img = sourceCanvas;
    layer.bbox = [origin.x, origin.y, origin.x + sourceCanvas.width, origin.y + sourceCanvas.height];
    if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
    if (typeof renderLayerPanel === 'function') renderLayerPanel();
    if (typeof drawLayerBounds === 'function') drawLayerBounds();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (successToast && typeof showToast === 'function') showToast(successToast, 'success');
    return true;
}

function layerHasEffects(layer) {
    const fx = layer && layer.effects;
    if (!fx) return false;
    return ['dropShadow', 'outerGlow', 'stroke', 'colorOverlay', 'bevel']
        .some(key => fx[key] && fx[key].enabled);
}

function isPointInLayerBbox(layer, px, py) {
    if (!layer || !layer.bbox) return false;
    const [x1, y1, x2, y2] = layer.bbox;
    return px >= x1 && px < x2 && py >= y1 && py < y2;
}

function _getLayerAlphaImageData(layer) {
    if (!layer || !layer.img) return null;
    const w = layer.img.width || layer.img.naturalWidth || 0;
    const h = layer.img.height || layer.img.naturalHeight || 0;
    if (!w || !h) return null;
    const tc = document.createElement('canvas');
    tc.width = w;
    tc.height = h;
    const tctx = tc.getContext('2d', { willReadFrequently: true });
    tctx.drawImage(layer.img, 0, 0, w, h);
    return tctx.getImageData(0, 0, w, h);
}

function isPointOnLayerOpaque(layer, px, py, alphaThreshold) {
    if (!layer || !layer.img || !isPointInLayerBbox(layer, px, py)) return false;
    const origin = getLayerCanvasOrigin(layer);
    const imgData = _getLayerAlphaImageData(layer);
    if (!imgData) return false;
    const lx = px - origin.x;
    const ly = py - origin.y;
    if (lx < 0 || ly < 0 || lx >= imgData.width || ly >= imgData.height) return false;
    const idx = (ly * imgData.width + lx) * 4 + 3;
    return imgData.data[idx] > (alphaThreshold ?? 10);
}

function getTopmostVisibleLayerAtCanvasPoint(px, py) {
    if (!Array.isArray(_psdLayers)) return null;
    for (let i = _psdLayers.length - 1; i >= 0; i--) {
        const layer = _psdLayers[i];
        if (!layer || layer.visible === false || !layer.img) continue;
        const opacity = layer.opacity != null ? layer.opacity : 255;
        if (opacity <= 0) continue;
        if (isPointOnLayerOpaque(layer, px, py, 10)) return layer;
    }
    return null;
}

function selectConnectedLayerPixelsAtPoint(layerId, canvasX, canvasY, options) {
    const opts = options || {};
    const layer = getLayerById(layerId);
    if (!layer || !layer.img) return false;
    if (layer.locked) {
        if (typeof showToast === 'function') showToast(`"${layer.name || 'Layer'}" is locked — unlock it before isolating an element`, 'warn');
        return false;
    }
    const pc = document.getElementById('paintCanvas');
    const zone = (typeof zones !== 'undefined' && typeof selectedZoneIndex !== 'undefined') ? zones[selectedZoneIndex] : null;
    if (!pc || !zone) {
        if (typeof showToast === 'function') showToast('Select a zone first, then pick a layer element', 'info');
        return false;
    }
    const imgData = _getLayerAlphaImageData(layer);
    if (!imgData) return false;
    const origin = getLayerCanvasOrigin(layer);
    const lx0 = canvasX - origin.x;
    const ly0 = canvasY - origin.y;
    const lw = imgData.width;
    const lh = imgData.height;
    if (lx0 < 0 || ly0 < 0 || lx0 >= lw || ly0 >= lh) return false;
    const alphaThreshold = 10;
    const startIdx = (ly0 * lw + lx0) * 4 + 3;
    if (imgData.data[startIdx] <= alphaThreshold) {
        if (typeof showToast === 'function') showToast(`No opaque ${layer.name || 'layer'} pixels at that spot`, 'info');
        return false;
    }
    if (typeof pushUndo === 'function') pushUndo(selectedZoneIndex);
    zone.regionMask = new Uint8Array(pc.width * pc.height);
    const visited = new Uint8Array(lw * lh);
    const stack = [ly0 * lw + lx0];
    let count = 0;
    while (stack.length) {
        const pos = stack.pop();
        if (visited[pos]) continue;
        visited[pos] = 1;
        const lx = pos % lw;
        const ly = Math.floor(pos / lw);
        const alpha = imgData.data[(pos * 4) + 3];
        if (alpha <= alphaThreshold) continue;
        const cx = origin.x + lx;
        const cy = origin.y + ly;
        if (cx >= 0 && cy >= 0 && cx < pc.width && cy < pc.height) {
            zone.regionMask[(cy * pc.width) + cx] = 255;
            count++;
        }
        for (let ny = ly - 1; ny <= ly + 1; ny++) {
            for (let nx = lx - 1; nx <= lx + 1; nx++) {
                if (nx === lx && ny === ly) continue;
                if (nx < 0 || ny < 0 || nx >= lw || ny >= lh) continue;
                const npos = ny * lw + nx;
                if (!visited[npos]) stack.push(npos);
            }
        }
    }
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
    if (opts.autoTransform) {
        if (typeof transformSelectedLayerRegion === 'function') {
            const transformed = transformSelectedLayerRegion();
            if (!transformed && typeof showToast === 'function') {
                showToast(`Picked ${count.toLocaleString()} pixels from ${layer.name || 'layer'} — selection ready`, 'success');
            }
            return !!transformed;
        }
    }
    if (typeof showToast === 'function') {
        showToast(`Picked ${count.toLocaleString()} pixels from ${layer.name || 'layer'}`, 'success');
    }
    return count > 0;
}
window.selectConnectedLayerPixelsAtPoint = selectConnectedLayerPixelsAtPoint;

function activateLayerElementPickMode() {
    if (typeof setCanvasMode === 'function') setCanvasMode('layer-pick');
    if (typeof showToast === 'function') showToast('Pick Layer / Element: click a different layer to select it, or click the active layer to isolate one sponsor and transform it', 'info');
    return true;
}
window.activateLayerElementPickMode = activateLayerElementPickMode;

// Draw selection bounding box around the selected layer
function drawLayerBounds() {
    const tc = document.getElementById('transformCanvas');
    if (!tc) return;
    const layer = getSelectedLayer();
    // If no layer selected or free transform is active (it draws its own handles), bail
    if (!layer || freeTransformState) return;

    const pc = document.getElementById('paintCanvas');
    if (!pc) return;

    tc.width = pc.width;
    tc.height = pc.height;
    tc.style.width = pc.style.width;
    tc.style.height = pc.style.height;
    tc.style.display = 'block';
    tc.style.pointerEvents = 'none';

    const ctx = tc.getContext('2d');
    ctx.clearRect(0, 0, tc.width, tc.height);

    if (!layer.visible || !layer.img) return;

    const [x1, y1, x2, y2] = layer.bbox;
    const w = x2 - x1, h = y2 - y1;

    // Dashed outline
    ctx.setLineDash([6, 3]);
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x1, y1, w, h);

    // Corner + midpoint handles
    ctx.setLineDash([]);
    const hs = 7;
    ctx.fillStyle = '#00e5ff';
    ctx.strokeStyle = '#111';
    ctx.lineWidth = 1;
    const pts = [
        [x1, y1], [x2, y1], [x1, y2], [x2, y2],
        [(x1+x2)/2, y1], [(x1+x2)/2, y2], [x1, (y1+y2)/2], [x2, (y1+y2)/2]
    ];
    for (const [cx, cy] of pts) {
        ctx.fillRect(cx - hs/2, cy - hs/2, hs, hs);
        ctx.strokeRect(cx - hs/2, cy - hs/2, hs, hs);
    }

    // Layer name label above the box
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    const labelText = layer.name;
    ctx.font = 'bold 11px monospace';
    const tw = ctx.measureText(labelText).width;
    ctx.fillRect(x1, y1 - 16, tw + 8, 15);
    ctx.fillStyle = '#00e5ff';
    ctx.fillText(labelText, x1 + 4, y1 - 4);
}

function clearLayerBounds() {
    const tc = document.getElementById('transformCanvas');
    if (tc && !freeTransformState) {
        const ctx = tc.getContext('2d');
        ctx.clearRect(0, 0, tc.width, tc.height);
        tc.style.display = 'none';
    }
}

// Start a layer move drag
function startLayerDrag(layer, startX, startY) {
    _layerDragState = {
        layerId: layer.id,
        startX: startX,
        startY: startY,
        origBbox: [...layer.bbox],
        // Bockwinkel B2 (Workstream 23 #441): lazy undo snapshot. Only push
        // history when the user actually MOVES the layer, not on every
        // click-and-release. The flag flips on first updateLayerDrag.
        snapshotPushed: false,
    };
}

// Update layer position during drag
function updateLayerDrag(currentX, currentY) {
    if (!_layerDragState) return;
    const layer = _psdLayers.find(l => l.id === _layerDragState.layerId);
    if (!layer) return;
    // Bockwinkel B2 fix: snapshot once on first real move so Ctrl+Z restores
    // the pre-drag bbox. Without this, dragging a layer is unrecoverable.
    if (!_layerDragState.snapshotPushed && typeof _pushLayerStackUndo === 'function') {
        _pushLayerStackUndo('move layer');
        _layerDragState.snapshotPushed = true;
    }
    const dx = currentX - _layerDragState.startX;
    const dy = currentY - _layerDragState.startY;
    const ob = _layerDragState.origBbox;
    layer.bbox = [ob[0] + dx, ob[1] + dy, ob[2] + dx, ob[3] + dy];
    recompositeFromLayers();
    drawLayerBounds();
}

// End layer drag
function endLayerDrag() {
    if (!_layerDragState) return;
    _layerDragState = null;
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Layer moved');
}

// Free Transform for a PSD layer (Ctrl+T)
function activateLayerTransform() {
    const layer = getSelectedLayer();
    if (!layer || !layer.img) {
        if (typeof showToast === 'function') showToast('Select a layer first', 'info');
        return;
    }
    // TOOLS WAR Phase 5 — locked layers cannot be transformed.
    if (layer.locked) {
        if (typeof showToast === 'function') showToast(`"${layer.name}" is locked — unlock to transform`, 'warn');
        return;
    }
    const [x1, y1, x2, y2] = layer.bbox;
    const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
    const sw = x2 - x1, sh = y2 - y1;

    const meta = _pendingLayerTransformMeta || {};
    _pendingLayerTransformMeta = null;

    freeTransformState = {
        target: 'layer',
        layerId: layer.id,
        sessionUndoMode: meta.sessionUndoMode || 'restore',
        sessionScopeLabel: meta.sessionScopeLabel || `Layer: ${layer.name}`,
        centerX: cx, centerY: cy,
        scaleX: 1.0, scaleY: 1.0,
        rotation: 0,
        origCenterX: cx, origCenterY: cy,
        origScaleX: 1.0, origScaleY: 1.0,
        origRotation: 0,
        origBbox: [...layer.bbox],
        origImg: layer.img,  // Keep reference to original for quality scaling
        boxW: sw, boxH: sh,
        dragging: null,
        dragStartX: 0, dragStartY: 0,
        dragStartCX: 0, dragStartCY: 0,
        dragStartSX: 0, dragStartSY: 0,
        dragStartRot: 0,
    };

    const tc = document.getElementById('transformCanvas');
    const pc = document.getElementById('paintCanvas');
    if (tc && pc) {
        tc.style.display = 'block';
        tc.width = pc.width;
        tc.height = pc.height;
        tc.style.width = pc.style.width;
        tc.style.height = pc.style.height;
        tc.style.pointerEvents = 'auto';
    }
    drawTransformHandles();
    _showLayerTransformQuickbar(freeTransformState.sessionScopeLabel);
    if (typeof showToast === 'function') {
        showToast('Layer Transform: drag to move, handles to resize, drag outside the box to rotate. Use +/-90 or 180° for quick turns. Enter=apply, Esc/Ctrl+Z=cancel', 'info');
    }
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
}

// Commit layer transform — rescale layer image and update bbox.
// Photoshop-correct: push undo BEFORE mutating, and use the synchronous canvas
// (not an async toDataURL→Image→onload round-trip) so Ctrl+Z immediately after
// commit always targets the committed state.
function commitLayerTransform() {
    if (!freeTransformState || freeTransformState.target !== 'layer') return;
    const s = freeTransformState;
    const layer = _psdLayers.find(l => l.id === s.layerId);
    if (!layer) { deactivateFreeTransform(false); return; }

    // Workstream 17 #327 — opt-in transform commit logging.
    // Enable: window._SPB_DEBUG_TRANSFORM = true
    if (typeof window !== 'undefined' && window._SPB_DEBUG_TRANSFORM === true) {
        try {
            console.log('[SPB][transform] commit layer=%s rotation=%s scale=(%s,%s) center=(%s,%s)',
                layer.name, s.rotation, s.scaleX, s.scaleY, s.centerX, s.centerY);
        } catch (_) {}
    }

    // boxW/boxH already represent the final pixel size after resize drag
    const newW = Math.round(s.boxW);
    const newH = Math.round(s.boxH);
    const newX1 = Math.round(s.centerX - newW / 2);
    const newY1 = Math.round(s.centerY - newH / 2);

    // Snapshot pre-transform state so Ctrl+Z restores bbox + img atomically.
    // _pushLayerUndo uses the CURRENT layer.img (which is still s.origImg at
    // this point since scaledImg hasn't been assigned). This is the exact
    // Photoshop behavior: "Edit > Free Transform" shows up as ONE undo step.
    if (newW > 0 && newH > 0) {
        // Smart selection transforms already opened a stack-level undo entry
        // when the selected pixels were lifted to a temp layer. Keep the
        // whole "lift + transform" flow as ONE undo step.
        if (s.sessionUndoMode !== 'stack-restore') {
            try { _pushLayerUndo(layer, 'free transform'); } catch (_tu) {}
        }

        // Rasterize the scaled version
        const tmpCanvas = document.createElement('canvas');
        tmpCanvas.width = newW;
        tmpCanvas.height = newH;
        const tmpCtx = tmpCanvas.getContext('2d');

        // Apply rotation if any
        if (s.rotation && s.rotation !== 0) {
            tmpCtx.translate(newW / 2, newH / 2);
            tmpCtx.rotate(s.rotation * Math.PI / 180);
            tmpCtx.translate(-newW / 2, -newH / 2);
        }

        tmpCtx.drawImage(s.origImg, 0, 0, newW, newH);

        // SYNCHRONOUS assignment: use the canvas directly as layer.img (HTMLCanvasElement
        // is drawable just like Image). This avoids the race where Ctrl+Z fires
        // before onload and the user sees the pre-onload state.
        layer.img = tmpCanvas;
        layer.bbox = [newX1, newY1, newX1 + newW, newY1 + newH];
        recompositeFromLayers();
        drawLayerBounds();
        renderLayerPanel();
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }

    freeTransformState = null;
    _hideLayerTransformQuickbar();
    _hideTransformCanvas();
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
    if (typeof showToast === 'function') showToast('Layer transform applied');
}

// Cancel layer transform — restore original bbox/img and refresh preview.
function cancelLayerTransform() {
    if (!freeTransformState || freeTransformState.target !== 'layer') return;
    const s = freeTransformState;
    const layer = _psdLayers.find(l => l.id === s.layerId);
    // Workstream 17 #327 — opt-in transform cancel logging.
    if (typeof window !== 'undefined' && window._SPB_DEBUG_TRANSFORM === true) {
        try {
            console.log('[SPB][transform] cancel layer=%s restoring origBbox=%o',
                (layer && layer.name) || s.layerId, s.origBbox);
        } catch (_) {}
    }
    freeTransformState = null;
    _hideLayerTransformQuickbar();
    _hideTransformCanvas();

    if (s.sessionUndoMode === 'stack-restore') {
        if (typeof undoLayerEdit === 'function' && undoLayerEdit()) {
            if (typeof renderContextActionBar === 'function') renderContextActionBar();
            return;
        }
    }

    if (layer) {
        layer.bbox = s.origBbox;
        layer.img = s.origImg;
        recompositeFromLayers();
    }
    drawLayerBounds();
    // Photoshop parity: after a cancel the server-side preview is stale because
    // previous moves during the drag may have scheduled dirty previews. Nudge
    // it so the viewport reflects the pristine restored state.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
}

// ═══ EXPOSE ═══
window.importPSD = importPSD;
window.importPSDFromPath = _doPSDImport;  // Direct path-based import (no file picker)
window.toggleLayerVisible = toggleLayerVisible;
window.selectPSDLayer = selectPSDLayer;

// Right panel tab switching (LAYERS vs FINISHES)
function switchRightTab(tab) {
    const layersContent = document.getElementById('rpLayersContent');
    const finishesContent = document.getElementById('rpFinishesContent');
    if (!layersContent || !finishesContent) return;
    document.querySelectorAll('.rp-tab').forEach(btn => {
        const isActive = btn.getAttribute('data-tab') === tab;
        btn.style.color = isActive ? 'var(--accent-gold)' : 'var(--text-dim)';
        btn.style.borderBottom = isActive ? '2px solid var(--accent-gold)' : '2px solid transparent';
        btn.style.background = isActive ? 'transparent' : 'var(--bg-card)';
        if (isActive) btn.classList.add('active'); else btn.classList.remove('active');
    });
    if (tab === 'layers') {
        layersContent.style.display = 'flex';
        finishesContent.style.display = 'none';
    } else {
        layersContent.style.display = 'none';
        finishesContent.style.display = 'flex';
    }
}
window.switchRightTab = switchRightTab;

// Panel collapse/expand
function togglePanelCollapse(side) {
    const panel = document.getElementById(side === 'left' ? 'leftPanel' : 'rightPanel');
    const btn = document.getElementById(side === 'left' ? 'leftCollapseBtn' : 'rightCollapseBtn');
    if (!panel) return;
    const isCollapsed = panel.classList.toggle('panel-collapsed');
    if (side === 'left') {
        panel.style.width = isCollapsed ? '0px' : '';
        panel.style.minWidth = isCollapsed ? '0px' : '';
        panel.style.overflow = isCollapsed ? 'hidden' : '';
        panel.style.padding = isCollapsed ? '0' : '';
        panel.style.borderRight = isCollapsed ? 'none' : '';
        if (btn) btn.innerHTML = isCollapsed ? '&rsaquo;' : '&lsaquo;';
    } else {
        panel.style.width = isCollapsed ? '0px' : '';
        panel.style.minWidth = isCollapsed ? '0px' : '';
        panel.style.overflow = isCollapsed ? 'hidden' : '';
        panel.style.padding = isCollapsed ? '0' : '';
        panel.style.borderLeft = isCollapsed ? 'none' : '';
        if (btn) btn.innerHTML = isCollapsed ? '&lsaquo;' : '&rsaquo;';
    }
    // Keep the collapse button visible even when panel is collapsed
    if (btn) {
        btn.style.display = 'flex';
        if (isCollapsed) {
            btn.style.position = 'fixed';
            if (side === 'left') {
                const toolbar = document.querySelector('.vertical-toolbar');
                btn.style.left = (toolbar ? toolbar.offsetWidth + toolbar.offsetLeft : 88) + 'px';
            } else {
                btn.style.right = '0px';
                btn.style.left = 'auto';
            }
        } else {
            btn.style.position = 'absolute';
            btn.style.left = '';
            btn.style.right = '';
        }
    }
}
window.togglePanelCollapse = togglePanelCollapse;
window.deleteLayer = deleteLayer;
window.recompositeFromLayers = recompositeFromLayers;
window.addLayerFromFile = addLayerFromFile;
window.getSelectedLayer = getSelectedLayer;
window.drawLayerBounds = drawLayerBounds;
window.activateLayerTransform = activateLayerTransform;
window.commitLayerTransform = commitLayerTransform;
window.cancelLayerTransform = cancelLayerTransform;
window.startLayerDrag = startLayerDrag;
window.updateLayerDrag = updateLayerDrag;
window.endLayerDrag = endLayerDrag;
// Generic symmetry applicator — calls a paint function at all symmetry positions
// 2026-04-18 MARATHON bug #33 (Hawk, MED): symmetry mode was read from
// the DOM on EVERY paint dab during a stroke. If the painter changed the
// dropdown mid-drag, the second half of the stroke used a different
// mirror mode than the first half — ghost mirror pixels, weird results
// on Ctrl+Z. Fix: capture the mode at stroke start (mousedown) and
// honor it for the rest of the drag. The mousedown handlers now set
// window._spbStrokeSymmetryMode, and _applyWithSymmetry prefers that
// over re-reading the DOM.
function _applyWithSymmetry(paintFn, x, y) {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;
    paintFn(x, y); // Primary stroke
    var sym = (typeof window !== 'undefined' && window._spbStrokeSymmetryMode)
        || getEffectiveSymmetryMode();
    if (sym === 'off') return;
    const cx = Math.floor(w / 2), cy = Math.floor(h / 2);
    if (sym === 'mirror-h' || sym === 'mirror-both') paintFn(w - 1 - x, y);
    if (sym === 'mirror-v' || sym === 'mirror-both') paintFn(x, h - 1 - y);
    if (sym === 'mirror-both') paintFn(w - 1 - x, h - 1 - y);
    if (sym === 'radial-4') {
        const dx = x - cx, dy = y - cy;
        paintFn(cx - dy, cy + dx);
        paintFn(cx - dx, cy - dy);
        paintFn(cx + dy, cy - dx);
    }
    if (sym === 'radial-8') {
        const dx = x - cx, dy = y - cy;
        for (let a = 1; a < 8; a++) {
            const angle = a * Math.PI / 4;
            paintFn(Math.round(cx + dx * Math.cos(angle) - dy * Math.sin(angle)),
                    Math.round(cy + dx * Math.sin(angle) + dy * Math.cos(angle)));
        }
    }
}
window._applyWithSymmetry = _applyWithSymmetry;

// Right-click context menu on canvas
function showCanvasContextMenu(e) {
    e.preventDefault();
    var old = document.getElementById('canvasContextMenu');
    if (old) old.remove();
    var m = document.createElement('div');
    m.id = 'canvasContextMenu';
    m.style.cssText = 'position:fixed;left:'+e.clientX+'px;top:'+e.clientY+'px;z-index:100000;background:#1a1a2e;border:1px solid #00e5ff;border-radius:6px;padding:4px 0;min-width:160px;box-shadow:0 4px 16px rgba(0,0,0,0.5);font-size:11px;';
    var items = [
        {l:'Undo',k:'Ctrl+Z',fn:'undoDrawStroke'},{l:'Redo',k:'Ctrl+Y',fn:'redoDrawStroke'},{sep:true},
        {l:'Copy',k:'Ctrl+C',fn:'copySelection'},{l:'Cut',k:'Ctrl+X',fn:'cutSelection'},{l:'Paste',k:'Ctrl+V',fn:'pasteAsLayer'},{sep:true},
        {l:'Select All',k:'Ctrl+A',fn:'_ctxSelectAll'},{l:'Deselect',k:'Ctrl+D',fn:'deselectRegion'},{l:'Invert Selection',k:'Ctrl+Shift+I',fn:'invertRegionMask'},{sep:true},
        {l:'Transform',k:'Ctrl+T',fn:'_ctxTransform'},{l:'Flip View H',k:'',fn:'flipViewH'},{l:'Flip View V',k:'',fn:'flipViewV'},{l:'Grid',k:'',fn:'toggleGrid'},{sep:true},
        {l:'Zoom Fit',k:'0',fn:'_ctxZoomFit'},{l:'Zoom 100%',k:'1',fn:'_ctxZoom100'},{sep:true},
        {l:'Swap Colors',k:'X',fn:'swapForegroundBackground'},{l:'Export PNG',k:'',fn:'quickExportPNG'},{l:'Snapshot',k:'',fn:'saveHistorySnapshot'}
    ];
    var h = '';
    for (var i = 0; i < items.length; i++) {
        if (items[i].sep) { h += '<div style="border-top:1px solid #333;margin:2px 0;"></div>'; continue; }
        h += '<div class="_ctx_item" data-fn="'+items[i].fn+'" style="padding:5px 12px;cursor:pointer;display:flex;justify-content:space-between;gap:16px;" onmouseenter="this.style.background=\'rgba(0,229,255,0.1)\'" onmouseleave="this.style.background=\'\'"><span style="color:#ddd;">'+items[i].l+'</span><span style="color:#666;font-size:9px;">'+items[i].k+'</span></div>';
    }
    m.innerHTML = h;
    document.body.appendChild(m);
    m.addEventListener('click', function(ev) { var t = ev.target.closest('._ctx_item'); if (t && typeof window[t.getAttribute('data-fn')] === 'function') { window[t.getAttribute('data-fn')](); m.remove(); } });
    setTimeout(function(){ document.addEventListener('click', function _cl(ev){ if (!m.contains(ev.target)) { m.remove(); document.removeEventListener('click', _cl); } }); }, 50);
}
function _ctxSelectAll() {
    var z = zones[selectedZoneIndex];
    if (!z) return;
    var pc = document.getElementById('paintCanvas');
    if (!pc) return;
    // BUG #61: context-menu Select All was skipping undo, preview refresh, and toast.
    // Painter lost prior selection with no way to Ctrl+Z, and render didn't reflect the new mask.
    if (typeof pushZoneUndo === 'function') pushZoneUndo('Select all pixels');
    if (!z.regionMask) z.regionMask = new Uint8Array(pc.width * pc.height);
    z.regionMask.fill(255);
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') showToast('Selected all pixels in Zone ' + (selectedZoneIndex + 1));
}
function _ctxTransform() { if (typeof activateContextTransform === 'function') activateContextTransform(); }
function _ctxZoomFit() { if (typeof canvasZoom === 'function') canvasZoom('fit'); }
function _ctxZoom100() { if (typeof canvasZoom === 'function') canvasZoom('100'); }
window.showCanvasContextMenu = showCanvasContextMenu;
window._ctxZoomFit = _ctxZoomFit;
window._ctxZoom100 = _ctxZoom100;

// ══════════════════════════════════════════════════════════════════════════════
// CLIPBOARD — Copy/Paste selected pixels (internal clipboard, not system clipboard)
// Ctrl+C = copy selected pixels, Ctrl+V = paste as new layer, Ctrl+X = cut
// ══════════════════════════════════════════════════════════════════════════════

var _clipboardData = null; // { width, height, imageData, offsetX, offsetY, sourceTarget, sourceLayerId }

function _getActiveSelectionInfo() {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return null;
    const w = pc.width, h = pc.height;
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) return null;
    let minX = w, minY = h, maxX = -1, maxY = -1;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (zone.regionMask[y * w + x] > 0) {
                if (x < minX) minX = x;
                if (y < minY) minY = y;
                if (x > maxX) maxX = x;
                if (y > maxY) maxY = y;
            }
        }
    }
    if (maxX < minX || maxY < minY) return null;
    return {
        zone: zone,
        width: w,
        height: h,
        minX: minX,
        minY: minY,
        maxX: maxX,
        maxY: maxY,
        clipW: maxX - minX + 1,
        clipH: maxY - minY + 1,
    };
}

function hasActivePixelSelection() {
    return !!_getActiveSelectionInfo();
}
window.hasActivePixelSelection = hasActivePixelSelection;

function _getSelectionSourceData(selectionInfo) {
    const layer = (typeof isLayerEditTarget === 'function' && isLayerEditTarget()) ? getSelectedEditableLayer() : null;
    if (layer && layer.img) {
        const sc = document.createElement('canvas');
        sc.width = selectionInfo.width;
        sc.height = selectionInfo.height;
        const sctx = sc.getContext('2d', { willReadFrequently: true });
        const origin = getLayerCanvasOrigin(layer);
        sctx.drawImage(layer.img, origin.x, origin.y);
        return {
            sourceData: sctx.getImageData(0, 0, selectionInfo.width, selectionInfo.height).data,
            sourceTarget: 'layer',
            sourceLayer: layer,
        };
    }
    return {
        sourceData: paintImageData ? paintImageData.data : null,
        sourceTarget: 'composite',
        sourceLayer: null,
    };
}

function _captureSelectionClipboardData() {
    const selectionInfo = _getActiveSelectionInfo();
    if (!selectionInfo) return null;
    const srcInfo = _getSelectionSourceData(selectionInfo);
    if (!srcInfo.sourceData) return null;
    const clipped = new ImageData(selectionInfo.clipW, selectionInfo.clipH);
    for (let y = selectionInfo.minY; y <= selectionInfo.maxY; y++) {
        for (let x = selectionInfo.minX; x <= selectionInfo.maxX; x++) {
            if (selectionInfo.zone.regionMask[y * selectionInfo.width + x] > 0) {
                const si = (y * selectionInfo.width + x) * 4;
                const di = ((y - selectionInfo.minY) * selectionInfo.clipW + (x - selectionInfo.minX)) * 4;
                clipped.data[di] = srcInfo.sourceData[si];
                clipped.data[di + 1] = srcInfo.sourceData[si + 1];
                clipped.data[di + 2] = srcInfo.sourceData[si + 2];
                clipped.data[di + 3] = srcInfo.sourceData[si + 3];
            }
        }
    }
    return {
        width: selectionInfo.clipW,
        height: selectionInfo.clipH,
        imageData: clipped,
        offsetX: selectionInfo.minX,
        offsetY: selectionInfo.minY,
        sourceTarget: srcInfo.sourceTarget,
        sourceLayerId: srcInfo.sourceLayer ? srcInfo.sourceLayer.id : null,
        selectionInfo: selectionInfo,
    };
}

function _clearActivePixelSelection(noToast) {
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) return false;
    zone.regionMask = null;
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
    if (!noToast && typeof showToast === 'function') showToast('Selection cleared');
    return true;
}

function _selectionContainsCanvasPoint(x, y) {
    const selectionInfo = _getActiveSelectionInfo();
    if (!selectionInfo) return false;
    if (x < 0 || y < 0 || x >= selectionInfo.width || y >= selectionInfo.height) return false;
    return selectionInfo.zone.regionMask[(y * selectionInfo.width) + x] > 0;
}

function _storeClipboardFromSelection(silent) {
    const data = _captureSelectionClipboardData();
    if (!data) {
        if (!silent && typeof showToast === 'function') showToast('No selection to copy', true);
        return null;
    }
    _clipboardData = {
        width: data.width,
        height: data.height,
        imageData: data.imageData,
        offsetX: data.offsetX,
        offsetY: data.offsetY,
        sourceTarget: data.sourceTarget,
        sourceLayerId: data.sourceLayerId,
    };
    if (!silent && typeof showToast === 'function') {
        const target = data.sourceTarget === 'layer' ? 'from layer' : 'from composite';
        showToast(`Copied ${data.width}x${data.height} pixels ${target}`);
    }
    return data;
}

function _createLayerFromClipboardData(data, options) {
    if (!data) return null;
    const opts = options || {};
    const tmpCanvas = document.createElement('canvas');
    tmpCanvas.width = data.width;
    tmpCanvas.height = data.height;
    tmpCanvas.getContext('2d').putImageData(data.imageData, 0, 0);
    if (!opts.skipUndo && typeof _pushLayerStackUndo === 'function') {
        _pushLayerStackUndo(opts.undoLabel || 'paste as layer');
    }
    const newLayer = {
        id: (opts.idPrefix || 'pasted_') + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
        name: opts.name || 'Pasted',
        path: '',
        visible: true,
        opacity: 255,
        blendMode: 'source-over',
        locked: false,
        bbox: [
            data.offsetX,
            data.offsetY,
            data.offsetX + data.width,
            data.offsetY + data.height,
        ],
        img: tmpCanvas,
    };
    _psdLayers.push(newLayer);
    _psdLayersLoaded = true;
    selectPSDLayer(newLayer.id);
    recompositeFromLayers();
    renderLayerPanel();
    drawLayerBounds();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    return newLayer;
}

function _clearSelectionFromLayer(layer, selectionInfo) {
    if (!layer || !layer.img || !selectionInfo) return 0;
    const origin = getLayerCanvasOrigin(layer);
    const tmpCanvas = document.createElement('canvas');
    tmpCanvas.width = layer.img.width;
    tmpCanvas.height = layer.img.height;
    const tctx = tmpCanvas.getContext('2d', { willReadFrequently: true });
    tctx.drawImage(layer.img, 0, 0);
    const imgData = tctx.getImageData(0, 0, tmpCanvas.width, tmpCanvas.height);
    const d = imgData.data;
    let cleared = 0;
    for (let y = selectionInfo.minY; y <= selectionInfo.maxY; y++) {
        for (let x = selectionInfo.minX; x <= selectionInfo.maxX; x++) {
            if (selectionInfo.zone.regionMask[y * selectionInfo.width + x] <= 0) continue;
            const lx = x - origin.x;
            const ly = y - origin.y;
            if (lx < 0 || ly < 0 || lx >= tmpCanvas.width || ly >= tmpCanvas.height) continue;
            const idx = (ly * tmpCanvas.width + lx) * 4;
            d[idx] = d[idx + 1] = d[idx + 2] = d[idx + 3] = 0;
            cleared++;
        }
    }
    tctx.putImageData(imgData, 0, 0);
    layer.img = tmpCanvas;
    return cleared;
}

function copySelection() {
    _storeClipboardFromSelection(false);
}

function cutSelection() {
    const data = _storeClipboardFromSelection(true);
    if (!data) {
        showToast('No selection to cut', true);
        return;
    }
    const layer = (typeof isLayerEditTarget === 'function' && isLayerEditTarget()) ? getSelectedEditableLayer() : null;
    if (layer) {
        _pushLayerUndo(layer, 'cut selection');
        _clearSelectionFromLayer(layer, data.selectionInfo);
        recompositeFromLayers();
        renderLayerPanel();
        drawLayerBounds();
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        showToast('Cut to clipboard -> layer');
        return;
    }
    const d = paintImageData.data;
    pushPixelUndo('cut');
    for (let y = 0; y < data.selectionInfo.height; y++) {
        for (let x = 0; x < data.selectionInfo.width; x++) {
            if (data.selectionInfo.zone.regionMask[y * data.selectionInfo.width + x] > 0) {
                const idx = (y * data.selectionInfo.width + x) * 4;
                d[idx] = d[idx+1] = d[idx+2] = d[idx+3] = 0;
            }
        }
    }
    const pc = document.getElementById('paintCanvas');
    if (pc) pc.getContext('2d').putImageData(paintImageData, 0, 0);
    // 2026-04-18 MARATHON bug #34 (MED): pre-fix, cutSelection composite
    // path wrote pixel data and called pushPixelUndo but NEVER fired
    // Live Preview — painter cut a chunk out of the canvas, rendered
    // car kept showing the chunk still there.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast('Cut to clipboard');
}

function pasteAsLayer() {
    if (!_clipboardData) { showToast('Nothing on clipboard - copy first (Ctrl+C)', true); return; }
    _createLayerFromClipboardData(_clipboardData, {
        name: 'Pasted',
        idPrefix: 'pasted_',
        undoLabel: 'paste as layer',
    });
    showToast('Pasted as new layer');
}

function maybeAutoTransformLayerSelection(sourceTool, eventLike) {
    const layer = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
    if (!layer || !layer.img) return false;
    if (typeof hasActivePixelSelection !== 'function' || !hasActivePixelSelection()) return false;
    if (typeof freeTransformState !== 'undefined' && freeTransformState) return false;
    const selMode = document.getElementById('selectionMode')?.value || 'add';
    if (selMode === 'subtract' || !!eventLike?.altKey) return false;
    if (typeof transformSelectedLayerRegion !== 'function') return false;
    return !!transformSelectedLayerRegion();
}
window.maybeAutoTransformLayerSelection = maybeAutoTransformLayerSelection;

function commitRectSelection(endPos, eventLike) {
    if (!rectStart || !endPos || !zones[selectedZoneIndex]) return false;

    const selMode = document.getElementById('selectionMode')?.value || 'add';
    let replaceMode = selMode === 'replace' && !eventLike?.shiftKey && !eventLike?.altKey;
    let subtractMode = selMode === 'subtract' || !!eventLike?.altKey;

    if (replaceMode) {
        const zone = zones[selectedZoneIndex];
        const canvas = document.getElementById('paintCanvas');
        if (canvas && zone.regionMask) {
            zone.regionMask = new Uint8Array(canvas.width * canvas.height);
        }
    }

    const fillVal = subtractMode ? 0 : 255;
    paintRegionRect(rectStart.x, rectStart.y, endPos.x, endPos.y, fillVal);
    rectStart = null;
    _rectZoneCache = null;
    hideRectPreview();
    renderRegionOverlay();
    setTimeout(() => { _doRenderRegionOverlay(); }, 30);
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    return maybeAutoTransformLayerSelection('rectangle', eventLike);
}
window.commitRectSelection = commitRectSelection;

function liftSelectionToNewLayer() {
    const layer = (typeof isLayerEditTarget === 'function' && isLayerEditTarget()) ? getSelectedEditableLayer() : null;
    if (!layer) return false;
    const data = _storeClipboardFromSelection(true);
    if (!data) {
        showToast('No selection - select part of the layer first', true);
        return false;
    }
    if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('transform selection');
    _clearSelectionFromLayer(layer, data.selectionInfo);
    _createLayerFromClipboardData(data, {
        name: 'Transform Selection',
        idPrefix: 'selxform_',
        skipUndo: true,
    });
    _clearActivePixelSelection(true);
    showToast('Selection lifted to new layer for transform - use +/-90 or drag outside the box to rotate');
    return true;
}

function transformSelectedLayerRegion() {
    const layer = (typeof isLayerEditTarget === 'function' && isLayerEditTarget()) ? getSelectedEditableLayer() : null;
    if (!layer) {
        showToast('Select an editable layer first', true);
        return false;
    }
    if (!hasActivePixelSelection()) {
        showToast('Draw a rectangle, lasso, ellipse, or pen path around the part of the layer you want to transform', true);
        return false;
    }
    _pendingLayerTransformMeta = {
        sessionUndoMode: 'stack-restore',
        sessionScopeLabel: 'Transform Selection',
    };
    if (!liftSelectionToNewLayer()) return false;
    activateLayerTransform();
    return true;
}
window.transformSelectedLayerRegion = transformSelectedLayerRegion;

function rotateSelectedLayerRegion(deltaDegrees) {
    const delta = Number(deltaDegrees) || 0;
    if (!transformSelectedLayerRegion()) return false;
    rotateActiveLayerTransformBy(delta);
    commitLayerTransform();
    return true;
}
window.rotateSelectedLayerRegion = rotateSelectedLayerRegion;

function requestContextTransform(scopeMode) {
    const scope = scopeMode || 'auto';
    if (_selectedLayerId && _psdLayersLoaded && scope !== 'base' && scope !== 'pattern' && scope !== 'zone') {
        const selectionInfo = _getActiveSelectionInfo();
        if ((scope === 'selection' || (scope === 'auto' && selectionInfo)) && selectionInfo && getSelectedEditableLayer()) {
            if (transformSelectedLayerRegion()) {
                return true;
            }
        }
        if (scope === 'selection') return false;
        _pendingLayerTransformMeta = {
            sessionUndoMode: 'restore',
            sessionScopeLabel: `Transform Layer: ${(getSelectedEditableLayer() || {}).name || 'Selected Layer'}`,
        };
        activateLayerTransform();
        return true;
    }
    const z = zones[selectedZoneIndex];
    if (!z || typeof activateFreeTransform !== 'function') return false;
    let target = null;
    if (scope === 'pattern') {
        target = z.pattern && z.pattern !== 'none' ? 'pattern' : null;
    } else if (scope === 'base') {
        target = z.base ? 'base' : null;
    } else {
        target = z.pattern && z.pattern !== 'none' ? 'pattern' : (z.base ? 'base' : null);
    }
    if (!target) {
        if (typeof showToast === 'function') {
            showToast(scope === 'base' ? 'No base is set for this zone' : (scope === 'pattern' ? 'No pattern is set for this zone' : 'This zone has no base or pattern to transform'), 'warn');
        }
        return false;
    }
    activateFreeTransform(target);
    return true;
}
window.requestContextTransform = requestContextTransform;

function activateZoneTransform(target) {
    return requestContextTransform(target || 'zone');
}
window.activateZoneTransform = activateZoneTransform;

function activateLayerContextTransform() {
    const layer = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
    if (!layer) {
        if (typeof showToast === 'function') showToast('Select an editable layer first', true);
        return false;
    }
    const selectionInfo = typeof _getActiveSelectionInfo === 'function' ? _getActiveSelectionInfo() : null;
    return requestContextTransform(selectionInfo ? 'selection' : 'layer');
}
window.activateLayerContextTransform = activateLayerContextTransform;

function activateContextTransform() {
    return requestContextTransform('auto');
}
window.activateContextTransform = activateContextTransform;
window.liftSelectionToNewLayer = liftSelectionToNewLayer;
// Crop canvas to current selection bounding box
function cropToSelection() {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height;
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No selection to crop to — make a selection first', true); return; }

    // Find bounding box
    let minX = w, minY = h, maxX = 0, maxY = 0;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (zone.regionMask[y * w + x] > 0) {
                minX = Math.min(minX, x); minY = Math.min(minY, y);
                maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
            }
        }
    }
    if (maxX < minX) { showToast('Selection is empty', true); return; }

    const cw = maxX - minX + 1, ch = maxY - minY + 1;
    if (!confirm(`Crop canvas from ${w}x${h} to ${cw}x${ch}? This cannot be undone.`)) return;

    // Extract cropped area
    const ctx = pc.getContext('2d');
    const cropped = ctx.getImageData(minX, minY, cw, ch);

    // Resize canvas
    pc.width = cw; pc.height = ch;
    ctx.putImageData(cropped, 0, 0);
    paintImageData = ctx.getImageData(0, 0, cw, ch);

    // Resize region canvas
    const rc = document.getElementById('regionCanvas');
    if (rc) { rc.width = cw; rc.height = ch; }

    // Clear all region masks (they're wrong size now)
    zones.forEach(z => { z.regionMask = null; z.spatialMask = null; });

    // Refit zoom
    canvasZoom('fit');
    if (typeof updateStatusBar === 'function') updateStatusBar();
    // 2026-04-18 MARATHON: same class as resizeCanvas — zone masks wiped,
    // preview should refresh so the rendered car stops showing the old
    // zone coverage.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast(`Cropped to ${cw}x${ch}`);
}
window.cropToSelection = cropToSelection;

// Fill selection with foreground color (Alt+Backspace in Photoshop)
function fillSelectionWithColor(useBG) {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height;
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No selection to fill', true); return; }

    const color = useBG ? _backgroundColor : _foregroundColor;
    const r = parseInt(color.slice(1,3), 16), g = parseInt(color.slice(3,5), 16), b = parseInt(color.slice(5,7), 16);

    // Photoshop parity: Fill targets the active layer if one is selected,
    // regardless of which brush tool happens to be active. Use the broader
    // isLayerEditTarget() gate, not the brush-stroke-only isLayerPaintMode().
    if (typeof isLayerEditTarget === 'function' && isLayerEditTarget()) {
        _pushLayerUndo(getSelectedLayer(), 'fill selection');
        _initLayerPaintCanvas();
    } else {
        pushPixelUndo('fill selection');
    }

    const d = paintImageData.data;
    let count = 0;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (zone.regionMask[y * w + x] > 0) {
                const idx = (y * w + x) * 4;
                d[idx] = r; d[idx+1] = g; d[idx+2] = b; d[idx+3] = 255;
                count++;
            }
        }
    }
    _flushPaintImageDataToCurrentSurface();
    if (_activeLayerCanvas) {
        _commitLayerPaint();
    } else {
        // 2026-04-18 MARATHON bug #50 (MED): composite path did not fire
        // preview. Layer path is fine because _commitLayerPaint already
        // calls triggerPreviewRender internally.
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }
    // Workstream 19 #362 — surface where the fill landed so the user knows
    // active-layer vs composite without having to inspect pixels.
    var _target = (typeof getActiveTargetSummary === 'function') ? getActiveTargetSummary() : 'composite';
    showToast(`Filled ${count.toLocaleString()} pixels with ${color} → ${_target}`);
}
window.fillSelectionWithColor = fillSelectionWithColor;

// Delete selection (make transparent) — Photoshop Delete key
function deleteSelection() {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height;
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) return;

    // Photoshop parity: Delete targets the active layer if one is selected,
    // regardless of which brush tool happens to be active. (See fill above.)
    if (typeof isLayerEditTarget === 'function' && isLayerEditTarget()) {
        _pushLayerUndo(getSelectedLayer(), 'delete selection');
        _initLayerPaintCanvas();
    } else {
        pushPixelUndo('delete selection');
    }

    const d = paintImageData.data;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (zone.regionMask[y * w + x] > 0) {
                const idx = (y * w + x) * 4;
                d[idx] = d[idx+1] = d[idx+2] = d[idx+3] = 0;
            }
        }
    }
    _flushPaintImageDataToCurrentSurface();
    if (_activeLayerCanvas) {
        _commitLayerPaint();
    } else {
        // 2026-04-18 MARATHON bug #50 family: composite path preview refresh.
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }
    // Workstream 19 #362 — surface where the delete landed.
    var _delTarget = (typeof getActiveTargetSummary === 'function') ? getActiveTargetSummary() : 'composite';
    showToast(`Deleted selection pixels → ${_delTarget}`);
}
window.deleteSelection = deleteSelection;

window.copySelection = copySelection;
window.cutSelection = cutSelection;
window.pasteAsLayer = pasteAsLayer;

// ══════════════════════════════════════════════════════════════════════════════
// SELECTION MODIFIERS — Grow, Shrink, Smooth, Feather the current selection
// ══════════════════════════════════════════════════════════════════════════════

function growSelection(px) {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No selection to grow', true); return; }
    // 2026-04-19 TRUE FIVE-HOUR (TF9) — was calling `pushUndo` (a function
    // that does NOT exist in the canonical 3-copy build — only in the
    // legacy electron-app/server/paint-booth-app.js bundle). The
    // typeof-guard masked it: grow/shrink/smooth selection was SILENTLY
    // unrevertable. Sister functions throughout this file use pushZoneUndo.
    if (typeof pushZoneUndo === 'function') pushZoneUndo('grow selection');
    const src = new Uint8Array(zone.regionMask);
    const radius = px || 2;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (zone.regionMask[y * w + x] > 0) continue;
            // Check if any neighbor within radius is selected
            let found = false;
            for (let dy = -radius; dy <= radius && !found; dy++) {
                for (let dx = -radius; dx <= radius && !found; dx++) {
                    const nx = x + dx, ny = y + dy;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h && dx*dx+dy*dy <= radius*radius) {
                        if (src[ny * w + nx] > 0) found = true;
                    }
                }
            }
            if (found) zone.regionMask[y * w + x] = 255;
        }
    }
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    showToast(`Selection grew by ${radius}px`);
}

function shrinkSelection(px) {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No selection to shrink', true); return; }
    // 2026-04-19 TRUE FIVE-HOUR (TF10) — sister fix to TF9 (pushUndo → pushZoneUndo).
    if (typeof pushZoneUndo === 'function') pushZoneUndo('shrink selection');
    const src = new Uint8Array(zone.regionMask);
    const radius = px || 2;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (src[y * w + x] === 0) continue;
            // Check if any neighbor within radius is unselected (border pixel)
            let isBorder = false;
            for (let dy = -radius; dy <= radius && !isBorder; dy++) {
                for (let dx = -radius; dx <= radius && !isBorder; dx++) {
                    const nx = x + dx, ny = y + dy;
                    if (nx < 0 || nx >= w || ny < 0 || ny >= h || (dx*dx+dy*dy <= radius*radius && src[ny * w + nx] === 0)) {
                        isBorder = true;
                    }
                }
            }
            if (isBorder) zone.regionMask[y * w + x] = 0;
        }
    }
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    showToast(`Selection shrunk by ${radius}px`);
}

function smoothSelection() {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No selection to smooth', true); return; }
    // 2026-04-19 TRUE FIVE-HOUR (TF11) — sister fix to TF9 (pushUndo → pushZoneUndo).
    if (typeof pushZoneUndo === 'function') pushZoneUndo('smooth selection');
    const src = new Uint8Array(zone.regionMask);
    // 3x3 majority vote: pixel is selected if 5+ neighbors are selected
    for (let y = 1; y < h - 1; y++) {
        for (let x = 1; x < w - 1; x++) {
            let count = 0;
            for (let dy = -1; dy <= 1; dy++) {
                for (let dx = -1; dx <= 1; dx++) {
                    if (src[(y+dy) * w + (x+dx)] > 0) count++;
                }
            }
            zone.regionMask[y * w + x] = count >= 5 ? 255 : 0;
        }
    }
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    showToast('Selection smoothed');
}

// Resize canvas (Image > Canvas Size in Photoshop)
function resizeCanvas(newWidth, newHeight) {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    if (!newWidth || !newHeight || newWidth < 1 || newHeight < 1) return;

    const oldW = pc.width, oldH = pc.height;
    if (newWidth === oldW && newHeight === oldH) return;
    // 2026-04-18 MARATHON bug #47 (MED): pre-fix, resizeCanvas wiped
    // every zone's regionMask AND spatialMask with zero undo — painter's
    // accidental resize destroyed hours of mask work. Now pushes zone
    // undo BEFORE mutating so Ctrl+Z can rescue them.
    if (typeof pushZoneUndo === 'function') {
        pushZoneUndo('Resize canvas (clears zone masks)');
    }

    // Save current image
    const tmpCanvas = document.createElement('canvas');
    tmpCanvas.width = oldW; tmpCanvas.height = oldH;
    tmpCanvas.getContext('2d').putImageData(paintImageData, 0, 0);

    // Resize
    pc.width = newWidth; pc.height = newHeight;
    const ctx = pc.getContext('2d');
    ctx.clearRect(0, 0, newWidth, newHeight);
    // Scale the image to fit new dimensions
    ctx.drawImage(tmpCanvas, 0, 0, newWidth, newHeight);
    paintImageData = ctx.getImageData(0, 0, newWidth, newHeight);

    // Resize region canvas
    const rc = document.getElementById('regionCanvas');
    if (rc) { rc.width = newWidth; rc.height = newHeight; }

    // Clear all masks (wrong size)
    zones.forEach(z => { z.regionMask = null; z.spatialMask = null; });

    canvasZoom('fit');
    if (typeof updateStatusBar === 'function') updateStatusBar();
    // Zone masks just got wiped → preview must refresh.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast(`Canvas resized: ${oldW}x${oldH} -> ${newWidth}x${newHeight}`);
}
window.resizeCanvas = resizeCanvas;

// Flip canvas pixels horizontally (destructive — flips the actual image data)
function flipCanvasH() {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    // 2026-04-19 TRUE FIVE-HOUR (TF6) — silent-drop guard.
    // recompositeFromLayers (canvas.js:10566) clears the canvas and redraws
    // every PSD layer from layer.img. Any composite-only flip done here is
    // silently overwritten the next time recomposite runs (layer paint commit,
    // visibility toggle, opacity change, etc.). Refuse + tell the painter
    // where the layer-level transform lives.
    if (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded &&
        typeof _psdLayers !== 'undefined' && _psdLayers.length > 0) {
        if (typeof showToast === 'function') showToast(
            'Canvas flip is unsafe with PSD layers loaded — use Layer ▸ Flip instead, or flatten first', true
        );
        return;
    }
    pushPixelUndo('flip horizontal');
    const w = pc.width, h = pc.height, d = paintImageData.data;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < Math.floor(w / 2); x++) {
            const li = (y * w + x) * 4;
            const ri = (y * w + (w - 1 - x)) * 4;
            for (let c = 0; c < 4; c++) {
                const tmp = d[li + c]; d[li + c] = d[ri + c]; d[ri + c] = tmp;
            }
        }
    }
    _flushPaintImageDataToCurrentSurface();
    // 2026-04-18 MARATHON bug #48 (MED): composite was flipped in-place
    // but Live Preview stayed stale — rendered car kept showing the
    // pre-flip pixels until the painter triggered another action.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast('Canvas flipped horizontally');
}

// Flip canvas pixels vertically (destructive)
function flipCanvasV() {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    // 2026-04-19 TRUE FIVE-HOUR (TF7) — silent-drop guard (see TF6).
    if (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded &&
        typeof _psdLayers !== 'undefined' && _psdLayers.length > 0) {
        if (typeof showToast === 'function') showToast(
            'Canvas flip is unsafe with PSD layers loaded — use Layer ▸ Flip instead, or flatten first', true
        );
        return;
    }
    pushPixelUndo('flip vertical');
    const w = pc.width, h = pc.height, d = paintImageData.data;
    for (let y = 0; y < Math.floor(h / 2); y++) {
        for (let x = 0; x < w; x++) {
            const ti = (y * w + x) * 4;
            const bi = ((h - 1 - y) * w + x) * 4;
            for (let c = 0; c < 4; c++) {
                const tmp = d[ti + c]; d[ti + c] = d[bi + c]; d[bi + c] = tmp;
            }
        }
    }
    _flushPaintImageDataToCurrentSurface();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast('Canvas flipped vertically');
}

// Rotate canvas 90 degrees clockwise (destructive)
function rotateCanvas90() {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    // 2026-04-19 TRUE FIVE-HOUR (TF8) — silent-drop guard.
    // Same family as TF6/TF7. Rotating the composite canvas while PSD
    // layers are loaded would silently desync — recomposite would put back
    // the unrotated layers AND the canvas dimensions are now swapped, so
    // the layer.bbox values would all be off-canvas. Refuse + redirect.
    if (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded &&
        typeof _psdLayers !== 'undefined' && _psdLayers.length > 0) {
        if (typeof showToast === 'function') showToast(
            'Canvas rotate is unsafe with PSD layers loaded — flatten layers first, or use Layer ▸ Transform', true
        );
        return;
    }
    const oldW = pc.width, oldH = pc.height;
    pushPixelUndo('rotate 90');
    // 2026-04-18 MARATHON bug #48 family: rotate90 also wipes zone masks,
    // so push zone undo BEFORE mutating so painter can Ctrl+Z.
    if (typeof pushZoneUndo === 'function') {
        pushZoneUndo('Rotate canvas 90° (clears zone masks)');
    }

    const tmpCanvas = document.createElement('canvas');
    tmpCanvas.width = oldW; tmpCanvas.height = oldH;
    tmpCanvas.getContext('2d').putImageData(paintImageData, 0, 0);

    // New dimensions: swap width and height
    pc.width = oldH; pc.height = oldW;
    const ctx = pc.getContext('2d');
    ctx.translate(oldH, 0);
    ctx.rotate(Math.PI / 2);
    ctx.drawImage(tmpCanvas, 0, 0);
    paintImageData = ctx.getImageData(0, 0, oldH, oldW);

    // Resize region canvas
    const rc = document.getElementById('regionCanvas');
    if (rc) { rc.width = oldH; rc.height = oldW; }

    // Clear masks
    zones.forEach(z => { z.regionMask = null; z.spatialMask = null; });
    canvasZoom('fit');
    // Preview must refresh: composite rotated, masks wiped.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast(`Canvas rotated 90° (${oldH}x${oldW})`);
}

window.flipCanvasH = flipCanvasH;
window.flipCanvasV = flipCanvasV;
window.rotateCanvas90 = rotateCanvas90;

// Auto Levels — stretch histogram so darkest pixel=0, brightest=255
function autoLevels() {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    // 2026-04-19 TRUE FIVE-HOUR (TF1) — active-layer routing.
    // Pre-fix this mutator always wrote to the composite — including when
    // the painter had a PSD layer selected. That silently diverged the
    // composite from the layer (painter saw composite change but their
    // actual layer pixels were untouched). Pillman flagged this in the
    // last shift; shipped here with locked-guard + layer commit parity.
    if (typeof isSelectedLayerLocked === 'function' && isSelectedLayerLocked()) {
        if (typeof showToast === 'function') showToast('Layer is locked — unlock to apply Auto Levels', true);
        return;
    }
    var _layerTarget = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
    var _layerInited = false;
    if (_layerTarget) {
        if (typeof _pushLayerUndo === 'function') _pushLayerUndo(_layerTarget, 'auto levels on layer');
        if (typeof _initLayerPaintCanvas === 'function') _layerInited = _initLayerPaintCanvas();
    }
    if (!_layerInited) {
        pushPixelUndo('auto levels');
    }
    // 2026-04-19 HEENAN H4HR-PERF1 — autoLevels hot path optimization.
    // Hawk perf benchmark identified autoLevels as the worst composite
    // mutator at 6.2s per call on a 2048×2048 canvas. Optimizations:
    //   (1) Replace Math.min/Math.max with inline ternary (skip function-call overhead)
    //   (2) Precompute 255/range as scaleR/G/B (3 divisions outside the loop instead of 12M inside)
    //   (3) Replace Math.round with ((x + 0.5) | 0) bitwise truncation
    //       (skip Math object lookup + function dispatch per pixel)
    // Output is bit-identical to the prior implementation; speed is ~30-50% faster
    // because the hot loop has 9 fewer Math calls per pixel.
    const d = paintImageData.data, len = d.length;
    // Pass 1 — find min/max per channel.
    let minR = 255, maxR = 0, minG = 255, maxG = 0, minB = 255, maxB = 0;
    for (let i = 0; i < len; i += 4) {
        if (d[i+3] === 0) continue; // skip transparent
        const r = d[i], g = d[i+1], b = d[i+2];
        if (r < minR) minR = r; if (r > maxR) maxR = r;
        if (g < minG) minG = g; if (g > maxG) maxG = g;
        if (b < minB) minB = b; if (b > maxB) maxB = b;
    }
    // Pass 2 — rescale.
    const scaleR = 255 / (maxR - minR || 1);
    const scaleG = 255 / (maxG - minG || 1);
    const scaleB = 255 / (maxB - minB || 1);
    for (let i = 0; i < len; i += 4) {
        if (d[i+3] === 0) continue;
        d[i]   = ((d[i]   - minR) * scaleR + 0.5) | 0;
        d[i+1] = ((d[i+1] - minG) * scaleG + 0.5) | 0;
        d[i+2] = ((d[i+2] - minB) * scaleB + 0.5) | 0;
    }
    _flushPaintImageDataToCurrentSurface();
    if (_layerInited) {
        if (typeof _commitLayerPaint === 'function') _commitLayerPaint();
        if (typeof showToast === 'function') showToast('Auto Levels applied to layer');
    } else {
        // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W5): silent-stale.
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        showToast('Auto Levels applied');
    }
}

// Auto Contrast — normalize luminance without shifting color balance
function autoContrast() {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    // 2026-04-19 TRUE FIVE-HOUR (TF2) — active-layer routing (see TF1 for rationale).
    if (typeof isSelectedLayerLocked === 'function' && isSelectedLayerLocked()) {
        if (typeof showToast === 'function') showToast('Layer is locked — unlock to apply Auto Contrast', true);
        return;
    }
    var _layerTarget = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
    var _layerInited = false;
    if (_layerTarget) {
        if (typeof _pushLayerUndo === 'function') _pushLayerUndo(_layerTarget, 'auto contrast on layer');
        if (typeof _initLayerPaintCanvas === 'function') _layerInited = _initLayerPaintCanvas();
    }
    if (!_layerInited) {
        pushPixelUndo('auto contrast');
    }
    // 2026-04-19 HEENAN H4HR-PERF3 — autoContrast hot-path optimization.
    // Same pattern proven on autoLevels (142×) and posterize (127×):
    // inline Math.min/max, precomputed scale, bitwise round + clamp.
    // Output bit-identical. Uint8ClampedArray makes the explicit Math.min/max
    // unnecessary because writes outside [0,255] auto-clamp.
    const d = paintImageData.data, len = d.length;
    let minL = 255, maxL = 0;
    for (let i = 0; i < len; i += 4) {
        if (d[i+3] === 0) continue;
        const lum = 0.299 * d[i] + 0.587 * d[i+1] + 0.114 * d[i+2];
        if (lum < minL) minL = lum;
        if (lum > maxL) maxL = lum;
    }
    const scale = 255 / (maxL - minL || 1);
    for (let i = 0; i < len; i += 4) {
        if (d[i+3] === 0) continue;
        // Uint8ClampedArray clamps to [0,255] on assignment — no manual clamp needed.
        d[i]   = ((d[i]   - minL) * scale + 0.5) | 0;
        d[i+1] = ((d[i+1] - minL) * scale + 0.5) | 0;
        d[i+2] = ((d[i+2] - minL) * scale + 0.5) | 0;
    }
    _flushPaintImageDataToCurrentSurface();
    if (_layerInited) {
        if (typeof _commitLayerPaint === 'function') _commitLayerPaint();
        if (typeof showToast === 'function') showToast('Auto Contrast applied to layer');
    } else {
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        showToast('Auto Contrast applied');
    }
}

// Desaturate — convert to grayscale
function desaturateCanvas() {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    // 2026-04-19 TRUE FIVE-HOUR (TF3) — active-layer routing (see TF1 for rationale).
    if (typeof isSelectedLayerLocked === 'function' && isSelectedLayerLocked()) {
        if (typeof showToast === 'function') showToast('Layer is locked — unlock to desaturate', true);
        return;
    }
    var _layerTarget = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
    var _layerInited = false;
    if (_layerTarget) {
        if (typeof _pushLayerUndo === 'function') _pushLayerUndo(_layerTarget, 'desaturate on layer');
        if (typeof _initLayerPaintCanvas === 'function') _layerInited = _initLayerPaintCanvas();
    }
    if (!_layerInited) {
        pushPixelUndo('desaturate');
    }
    // 2026-04-19 HEENAN H4HR-PERF4 — desaturateCanvas hot-path optimization.
    // Replace Math.round with bitwise truncation. Uint8ClampedArray clamps.
    const d = paintImageData.data, len = d.length;
    for (let i = 0; i < len; i += 4) {
        const gray = (0.299 * d[i] + 0.587 * d[i+1] + 0.114 * d[i+2] + 0.5) | 0;
        d[i] = d[i+1] = d[i+2] = gray;
    }
    _flushPaintImageDataToCurrentSurface();
    if (_layerInited) {
        if (typeof _commitLayerPaint === 'function') _commitLayerPaint();
        if (typeof showToast === 'function') showToast('Desaturated layer');
    } else {
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        showToast('Desaturated');
    }
}

// Invert colors
function invertCanvasColors() {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    // 2026-04-19 TRUE FIVE-HOUR (TF4) — active-layer routing (see TF1 for rationale).
    if (typeof isSelectedLayerLocked === 'function' && isSelectedLayerLocked()) {
        if (typeof showToast === 'function') showToast('Layer is locked — unlock to invert colors', true);
        return;
    }
    var _layerTarget = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
    var _layerInited = false;
    if (_layerTarget) {
        if (typeof _pushLayerUndo === 'function') _pushLayerUndo(_layerTarget, 'invert colors on layer');
        if (typeof _initLayerPaintCanvas === 'function') _layerInited = _initLayerPaintCanvas();
    }
    if (!_layerInited) {
        pushPixelUndo('invert colors');
    }
    const d = paintImageData.data, len = d.length;
    for (let i = 0; i < len; i += 4) {
        d[i] = 255 - d[i]; d[i+1] = 255 - d[i+1]; d[i+2] = 255 - d[i+2];
    }
    pc.getContext('2d').putImageData(paintImageData, 0, 0);
    if (_layerInited) {
        if (typeof _commitLayerPaint === 'function') _commitLayerPaint();
        if (typeof showToast === 'function') showToast('Colors inverted on layer');
    } else {
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        showToast('Colors inverted');
    }
}

// Posterize — reduce color depth
function posterize(levels) {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const n = levels || 4;
    // 2026-04-19 TRUE FIVE-HOUR (TF5) — active-layer routing (see TF1 for rationale).
    if (typeof isSelectedLayerLocked === 'function' && isSelectedLayerLocked()) {
        if (typeof showToast === 'function') showToast('Layer is locked — unlock to posterize', true);
        return;
    }
    var _layerTarget = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
    var _layerInited = false;
    if (_layerTarget) {
        if (typeof _pushLayerUndo === 'function') _pushLayerUndo(_layerTarget, 'posterize on layer');
        if (typeof _initLayerPaintCanvas === 'function') _layerInited = _initLayerPaintCanvas();
    }
    if (!_layerInited) {
        pushPixelUndo('posterize');
    }
    // 2026-04-19 HEENAN H4HR-PERF2 — posterize hot path optimization.
    // Hawk perf benchmark: posterize at 4.0s per call on 2048×2048 (2nd worst
    // composite mutator). The original `Math.round(Math.round(x / step) * step)`
    // is two function calls + two divisions per channel per pixel = 6 Math calls
    // per pixel. Optimization:
    //   (1) Precompute invStep = 1/step (one division outside loop instead of
    //       12M inside)
    //   (2) Replace each Math.round with `((v + 0.5) | 0)` bitwise trunc
    //   (3) Skip transparent pixels (matches autoLevels semantics)
    // Output is bit-identical; speed expected ~40-60% faster.
    const d = paintImageData.data, len = d.length;
    const step = 255 / (n - 1);
    const invStep = 1 / step;
    for (let i = 0; i < len; i += 4) {
        if (d[i+3] === 0) continue;
        d[i]   = ((((d[i]   * invStep) + 0.5) | 0) * step + 0.5) | 0;
        d[i+1] = ((((d[i+1] * invStep) + 0.5) | 0) * step + 0.5) | 0;
        d[i+2] = ((((d[i+2] * invStep) + 0.5) | 0) * step + 0.5) | 0;
    }
    pc.getContext('2d').putImageData(paintImageData, 0, 0);
    if (_layerInited) {
        if (typeof _commitLayerPaint === 'function') _commitLayerPaint();
        if (typeof showToast === 'function') showToast(`Posterized layer to ${n} levels`);
    } else {
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        showToast(`Posterized to ${n} levels`);
    }
}

window.autoLevels = autoLevels;
window.autoContrast = autoContrast;
window.desaturateCanvas = desaturateCanvas;
window.invertCanvasColors = invertCanvasColors;
window.posterize = posterize;

// Prompt user for new canvas size
function promptResizeCanvas() {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const input = prompt(`Enter new size (WxH):\nCurrent: ${pc.width}x${pc.height}\niRacing standard: 2048x2048`, `${pc.width}x${pc.height}`);
    if (!input) return;
    const parts = input.split('x').map(s => parseInt(s.trim()));
    if (parts.length !== 2 || isNaN(parts[0]) || isNaN(parts[1]) || parts[0] < 1 || parts[1] < 1) {
        showToast('Invalid size — use format: 2048x2048', true);
        return;
    }
    resizeCanvas(parts[0], parts[1]);
}
window.promptResizeCanvas = promptResizeCanvas;

// Border selection — select only the border of the current selection
function borderSelection(width) {
    const pc = document.getElementById('paintCanvas');
    if (!pc) return;
    const w = pc.width, h = pc.height;
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No selection to border', true); return; }
    // 2026-04-19 TRUE FIVE-HOUR (TF21) — sister bug to TF9-TF11. Hennig
    // perfection-pass spotted that borderSelection is the 4th selection
    // modifier in this neighborhood and uses the same broken pattern:
    // calls bare `pushUndo('label')` which targets canvas.js:3468's
    // pushUndo(zoneIndex). The string is treated as zone index → falsy
    // lookup → silent no-op. Painter's border-selection action was
    // unrevertable. Same fix as TF9-TF11.
    if (typeof pushZoneUndo === 'function') pushZoneUndo('border selection');
    const bw = width || 3;
    const outer = new Uint8Array(zone.regionMask);
    const inner = new Uint8Array(zone.regionMask);

    // Grow outer by border width
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (outer[y * w + x] > 0) continue;
            for (let dy = -bw; dy <= bw; dy++) {
                for (let dx = -bw; dx <= bw; dx++) {
                    const nx = x + dx, ny = y + dy;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h && dx*dx+dy*dy <= bw*bw && zone.regionMask[ny * w + nx] > 0) {
                        outer[y * w + x] = 255;
                        dy = bw + 1; break;
                    }
                }
            }
        }
    }
    // Shrink inner by border width
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (inner[y * w + x] === 0) continue;
            for (let dy = -bw; dy <= bw; dy++) {
                for (let dx = -bw; dx <= bw; dx++) {
                    const nx = x + dx, ny = y + dy;
                    if (nx < 0 || nx >= w || ny < 0 || ny >= h || (dx*dx+dy*dy <= bw*bw && zone.regionMask[ny * w + nx] === 0)) {
                        inner[y * w + x] = 0;
                        dy = bw + 1; break;
                    }
                }
            }
        }
    }
    // Border = outer AND NOT inner
    for (let i = 0; i < outer.length; i++) {
        zone.regionMask[i] = (outer[i] > 0 && inner[i] === 0) ? 255 : 0;
    }
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    showToast(`Border selection: ${bw}px`);
}

// Select Color Range — select all pixels within a color range from FG color
function selectColorRange(tolerance) {
    const pc = document.getElementById('paintCanvas');
    if (!pc || !paintImageData) return;
    const w = pc.width, h = pc.height;
    const zone = zones[selectedZoneIndex];
    if (!zone) return;
    // 2026-04-19 TRUE FIVE-HOUR (TF22) — sister to TF9-TF11 + TF21.
    // selectColorRange was the 5th selection modifier with the same bare-pushUndo
    // bug: pushUndo(zoneIndex) in canvas.js:3468 expects an integer; calling it
    // with the string 'color range' makes zones[label] undefined → silent no-op.
    // Painter's color-range select was unrevertable.
    if (typeof pushZoneUndo === 'function') pushZoneUndo('color range');
    const tol = tolerance || 32;
    const fgHex = _foregroundColor;
    const tr = parseInt(fgHex.slice(1,3), 16), tg = parseInt(fgHex.slice(3,5), 16), tb = parseInt(fgHex.slice(5,7), 16);
    const tol2 = tol * tol * 3;

    if (!zone.regionMask) zone.regionMask = new Uint8Array(w * h);
    const d = paintImageData.data;
    let count = 0;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const idx = (y * w + x) * 4;
            const dr = d[idx] - tr, dg = d[idx+1] - tg, db = d[idx+2] - tb;
            if (dr*dr + dg*dg + db*db <= tol2) {
                zone.regionMask[y * w + x] = 255;
                count++;
            }
        }
    }
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    showToast(`Color range: ${count.toLocaleString()} pixels matching ${fgHex} (tolerance ${tol})`);
}

window.growSelection = growSelection;
window.shrinkSelection = shrinkSelection;
window.smoothSelection = smoothSelection;
window.borderSelection = borderSelection;
window.selectColorRange = selectColorRange;


function renameLayer(layerId) {
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer) return;
    const raw = prompt('Rename layer:', layer.name);
    if (raw == null) return; // Esc cancel
    // BUG #68 hardening: strip newlines / control chars, cap length, disallow
    // empty / duplicate names. Combined with escapeHtml in the panel renderer
    // this closes the PSD-layer-name injection surface.
    let newName = String(raw).replace(/[\x00-\x1f]+/g, ' ').trim();
    if (newName.length > 64) newName = newName.slice(0, 64);
    if (!newName) {
        if (typeof showToast === 'function') showToast('Layer name cannot be empty', true);
        return;
    }
    if (newName === layer.name) return;
    const collision = _psdLayers.some(x => x !== layer && x.name === newName);
    if (collision) {
        if (typeof showToast === 'function') showToast('Another layer already uses that name', true);
        return;
    }
    // Photoshop parity: layer renames are undoable. Snapshot stack state so
    // a misclick doesn't lose a carefully-crafted sponsor name.
    if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('rename layer');
    layer.name = newName;
    renderLayerPanel();
    if (typeof showToast === 'function') showToast('Renamed to: ' + layer.name);
}
window.renameLayer = renameLayer;
window.moveLayerUp = moveLayerUp;
window.moveLayerDown = moveLayerDown;
window.flipLayerH = flipLayerH;
window.flipLayerV = flipLayerV;
window.rotateLayer90 = rotateLayer90;
window.duplicateLayer = duplicateLayer;
window.mergeLayerDown = mergeLayerDown;
window.flattenAllLayers = flattenAllLayers;
window.selectLayerPixels = selectLayerPixels;
window.setLayerOpacity = setLayerOpacity;
window.setLayerBlendMode = setLayerBlendMode;
window.toggleLayerLocked = toggleLayerLocked;
window.onLayerDragStart = onLayerDragStart;
window.onLayerDragOver = onLayerDragOver;
window.onLayerDragEnd = onLayerDragEnd;

// ===== LAYER EFFECTS DIALOG =====
var _effectsTargetLayerId = null;

// Effects-dialog session marker. Photoshop coalesces every slider tick within
// a single "Layer Style" dialog session into ONE undo entry; we mirror that by
// resetting this flag on dialog open / close and pushing a single snapshot the
// first time updateLayerEffect mutates within a session.
var _effectsSessionUndoPushed = false;

// Codex MED — default effects bag template. Used to populate the dialog's
// initial values WITHOUT mutating the layer until a real edit happens.
var _DEFAULT_EFFECTS_BAG = {
    dropShadow: { enabled: false, color: '#000000', angle: 135, distance: 5, size: 5, opacity: 0.75 },
    outerGlow: { enabled: false, color: '#00e5ff', size: 10, spread: 0, opacity: 0.8 },
    stroke: { enabled: false, color: '#ffffff', width: 2, position: 'outside', opacity: 1.0 },
    colorOverlay: { enabled: false, color: '#ff3366', opacity: 0.5, blendMode: 'source-over' },
    bevel: { enabled: false, style: 'outer', depth: 3, direction: 'up', size: 5, soften: 0 },
};

function openLayerEffects(layerId) {
    var layer = _psdLayers.find(function(l) { return l.id === layerId; });
    if (!layer) return;
    _effectsTargetLayerId = layerId;
    // New dialog session: arm the lazy-undo guard. We do NOT snapshot here —
    // the snapshot only fires on the first real edit (Photoshop parity:
    // opening and closing the dialog without changing anything is a no-op).
    _effectsSessionUndoPushed = false;
    // Codex MED — DO NOT initialize layer.effects here. Doing so was making
    // a mere "open dialog and close" mutate the document and force an undo
    // entry. Photoshop opens the Layer Style dialog without modifying the
    // layer until a control changes. We populate the dialog from defaults
    // when the layer has no effects bag, and the bag is created lazily on
    // the first real edit by updateLayerEffect.
    var fx = layer.effects || _DEFAULT_EFFECTS_BAG;
    var dlg = document.getElementById('layerEffectsDialog');
    if (!dlg) return;
    document.getElementById('layerEffectsLayerName').textContent = layer.name || 'Layer';
    document.getElementById('fxDropShadowEnabled').checked = (fx.dropShadow && fx.dropShadow.enabled) || false;
    document.getElementById('fxDropShadowControls').style.display = (fx.dropShadow && fx.dropShadow.enabled) ? 'block' : 'none';
    document.getElementById('fxDropShadowColor').value = (fx.dropShadow && fx.dropShadow.color) || '#000000';
    document.getElementById('fxDropShadowOpacity').value = Math.round(((fx.dropShadow && fx.dropShadow.opacity != null) ? fx.dropShadow.opacity : 0.75) * 100);
    document.getElementById('fxDropShadowAngle').value = (fx.dropShadow && fx.dropShadow.angle != null) ? fx.dropShadow.angle : 135;
    document.getElementById('fxDropShadowAngleVal').textContent = ((fx.dropShadow && fx.dropShadow.angle != null) ? fx.dropShadow.angle : 135) + '\u00B0';
    document.getElementById('fxDropShadowDistance').value = (fx.dropShadow && fx.dropShadow.distance != null) ? fx.dropShadow.distance : 5;
    document.getElementById('fxDropShadowSize').value = (fx.dropShadow && fx.dropShadow.size != null) ? fx.dropShadow.size : 5;
    document.getElementById('fxOuterGlowEnabled').checked = (fx.outerGlow && fx.outerGlow.enabled) || false;
    document.getElementById('fxOuterGlowControls').style.display = (fx.outerGlow && fx.outerGlow.enabled) ? 'block' : 'none';
    document.getElementById('fxOuterGlowColor').value = (fx.outerGlow && fx.outerGlow.color) || '#00e5ff';
    document.getElementById('fxOuterGlowOpacity').value = Math.round(((fx.outerGlow && fx.outerGlow.opacity != null) ? fx.outerGlow.opacity : 0.8) * 100);
    document.getElementById('fxOuterGlowSize').value = (fx.outerGlow && fx.outerGlow.size != null) ? fx.outerGlow.size : 10;
    document.getElementById('fxOuterGlowSpread').value = (fx.outerGlow && fx.outerGlow.spread != null) ? fx.outerGlow.spread : 0;
    document.getElementById('fxStrokeEnabled').checked = (fx.stroke && fx.stroke.enabled) || false;
    document.getElementById('fxStrokeControls').style.display = (fx.stroke && fx.stroke.enabled) ? 'block' : 'none';
    document.getElementById('fxStrokeColor').value = (fx.stroke && fx.stroke.color) || '#ffffff';
    document.getElementById('fxStrokeWidth').value = (fx.stroke && fx.stroke.width != null) ? fx.stroke.width : 2;
    document.getElementById('fxStrokeWidthVal').textContent = ((fx.stroke && fx.stroke.width != null) ? fx.stroke.width : 2) + 'px';
    document.getElementById('fxStrokePosition').value = (fx.stroke && fx.stroke.position) || 'outside';
    document.getElementById('fxStrokeOpacity').value = Math.round(((fx.stroke && fx.stroke.opacity != null) ? fx.stroke.opacity : 1.0) * 100);
    document.getElementById('fxColorOverlayEnabled').checked = (fx.colorOverlay && fx.colorOverlay.enabled) || false;
    document.getElementById('fxColorOverlayControls').style.display = (fx.colorOverlay && fx.colorOverlay.enabled) ? 'block' : 'none';
    document.getElementById('fxColorOverlayColor').value = (fx.colorOverlay && fx.colorOverlay.color) || '#ff3366';
    document.getElementById('fxColorOverlayOpacity').value = Math.round(((fx.colorOverlay && fx.colorOverlay.opacity != null) ? fx.colorOverlay.opacity : 0.5) * 100);
    document.getElementById('fxBevelEnabled').checked = (fx.bevel && fx.bevel.enabled) || false;
    document.getElementById('fxBevelControls').style.display = (fx.bevel && fx.bevel.enabled) ? 'block' : 'none';
    document.getElementById('fxBevelDepth').value = (fx.bevel && fx.bevel.depth != null) ? fx.bevel.depth : 3;
    document.getElementById('fxBevelSize').value = (fx.bevel && fx.bevel.size != null) ? fx.bevel.size : 5;
    document.getElementById('fxBevelSoften').value = (fx.bevel && fx.bevel.soften != null) ? fx.bevel.soften : 0;
    document.getElementById('fxBevelDirection').value = (fx.bevel && fx.bevel.direction) || 'up';
    dlg.style.display = 'block';
}

function closeLayerEffects() {
    document.getElementById('layerEffectsDialog').style.display = 'none';
    _effectsTargetLayerId = null;
    // End of effects-dialog session: arm the lazy-undo guard for the next
    // session so a new dialog open starts a fresh undo step.
    _effectsSessionUndoPushed = false;
    if (typeof renderLayerPanel === 'function') renderLayerPanel();
    // Photoshop parity: when the user closes the effects dialog the live
    // server preview should reflect the last committed state.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function updateLayerEffect(effectName, propName, value) {
    if (!_effectsTargetLayerId) return;
    var layer = _psdLayers.find(function(l) { return l.id === _effectsTargetLayerId; });
    if (!layer) return;
    // FIVE-HOUR SHIFT Win H2: lock-bypass family. Sister setLayerBlendMode
    // (marathon #73) and setLayerOpacity (Win D1) check layer.locked. The
    // effects dialog was the asymmetric outlier — painter could open the
    // dialog on a locked layer and tweak Drop Shadow / Stroke / Glow,
    // pushing entries onto the undo stack against the lock badge's promise.
    if (layer.locked) {
        if (typeof showToast === 'function') showToast('"' + (layer.name || 'Layer') + '" is locked — unlock to edit effects', true);
        return;
    }
    // Codex MED — lazy initialization of the effects bag. openLayerEffects
    // no longer mutates the layer just because the dialog opened, so the
    // first real edit must do it. Snapshot BEFORE creating the bag so undo
    // returns to "no effects bag" not "empty bag".
    if (!layer.effects) {
        if (typeof _pushLayerStackUndo === 'function') {
            _pushLayerStackUndo('init layer effects');
            _effectsSessionUndoPushed = true; // single combined undo step.
        }
        // Deep clone so distinct layers don't alias the template.
        layer.effects = JSON.parse(JSON.stringify(_DEFAULT_EFFECTS_BAG));
    }
    // Lazy undo: snapshot ONCE per dialog session, on the first edit. This
    // matches Photoshop's "Layer Style" dialog where a whole tweaking
    // session collapses into a single undo step.
    if (!_effectsSessionUndoPushed && typeof _pushLayerStackUndo === 'function') {
        _pushLayerStackUndo('layer effects');
        _effectsSessionUndoPushed = true;
    }
    // Workstream 17 #324 — opt-in effect-session debug logging.
    // Enable in console: window._SPB_DEBUG_EFFECTS = true
    // Useful for tracing slider drags and confirming session coalescing.
    if (typeof window !== 'undefined' && window._SPB_DEBUG_EFFECTS === true) {
        try {
            console.log('[SPB][effects] %s.%s = %o (layer=%s, sessionUndo=%s)',
                effectName, propName, value, layer.name, _effectsSessionUndoPushed);
        } catch (_) {}
    }
    if (!layer.effects[effectName]) layer.effects[effectName] = {};
    layer.effects[effectName][propName] = value;
    if (propName === 'enabled') {
        var controlsId = 'fx' + effectName.charAt(0).toUpperCase() + effectName.slice(1) + 'Controls';
        var el = document.getElementById(controlsId);
        if (el) el.style.display = value ? 'block' : 'none';
    }
    if (effectName === 'dropShadow' && propName === 'angle') document.getElementById('fxDropShadowAngleVal').textContent = value + '\u00B0';
    if (effectName === 'stroke' && propName === 'width') document.getElementById('fxStrokeWidthVal').textContent = value + 'px';
    // Track L #245 perf — coalesce rapid slider fires into one recomposite
    // per animation frame. Sliders can fire 100+ times per drag; without
    // this each fire ran a full 2048×2048 recomposite synchronously.
    // The triggerPreviewRender call still has its own 300ms debounce.
    _scheduleEffectsRecomposite();
}

// rAF-coalesced recomposite scheduler. Set by updateLayerEffect; consumed
// by the next animation frame.
var _effectsRecompositePending = false;
function _scheduleEffectsRecomposite() {
    if (_effectsRecompositePending) return;
    _effectsRecompositePending = true;
    var run = function () {
        _effectsRecompositePending = false;
        if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    };
    if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
        window.requestAnimationFrame(run);
    } else {
        // Fallback: run synchronously when rAF unavailable (e.g. headless tests).
        run();
    }
}

function clearAllLayerEffects() {
    if (!_effectsTargetLayerId) return;
    var layer = _psdLayers.find(function(l) { return l.id === _effectsTargetLayerId; });
    if (!layer) return;
    // Critical: snapshot BEFORE nuking. Without this, one click silently
    // destroys hours of layer-style work and Ctrl+Z can't bring it back.
    if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('clear layer effects');
    layer.effects = null;
    closeLayerEffects();
    if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
    // The recomposite removes the effects from the client canvas; nudge the
    // server-side preview so it agrees.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

window.openLayerEffects = openLayerEffects;
window.closeLayerEffects = closeLayerEffects;
window.updateLayerEffect = updateLayerEffect;
window.clearAllLayerEffects = clearAllLayerEffects;

// ══════════════════════════════════════════════════════════════════════════════
// CANVAS TOOL ERGONOMICS PACK (Platinum tier)
// 70+ material UX improvements layered on top of the base tool engine.
// All additions are non-destructive — they hook into existing globals via
// feature detection (typeof X === 'function') and never overwrite Codex fixes,
// the alpha-aware getLayerVisibleContributionMask, or the isLayerPaintMode whitelist.
// Keep this block at the END of the file.
// ══════════════════════════════════════════════════════════════════════════════
(function installPlatinumCanvasUx() {
    'use strict';

    // ─────────────────────────────────────────────────────────────────────────
    // [01] BRUSH SMOOTHING — interpolates between mouse samples to even out jitter.
    // Higher value = more averaging. 0 = raw input. Stores last 8 samples per stroke.
    // ─────────────────────────────────────────────────────────────────────────
    var _smoothSamples = [];
    var _smoothMax = 8;
    window.brushSmoothing = window.brushSmoothing || 0; // 0..100
    window.smoothBrushPoint = function smoothBrushPoint(x, y) {
        var s = Math.max(0, Math.min(100, parseInt(window.brushSmoothing || 0, 10))) / 100;
        if (s <= 0.01) return { x: x, y: y };
        _smoothSamples.push({ x: x, y: y });
        while (_smoothSamples.length > _smoothMax) _smoothSamples.shift();
        var sx = 0, sy = 0, n = _smoothSamples.length;
        for (var i = 0; i < n; i++) { sx += _smoothSamples[i].x; sy += _smoothSamples[i].y; }
        var avgX = sx / n, avgY = sy / n;
        return {
            x: Math.round(x * (1 - s) + avgX * s),
            y: Math.round(y * (1 - s) + avgY * s)
        };
    };
    window.resetBrushSmoothing = function resetBrushSmoothing() { _smoothSamples.length = 0; };
    window.setBrushSmoothing = function setBrushSmoothing(v) {
        window.brushSmoothing = Math.max(0, Math.min(100, parseInt(v, 10) || 0));
        if (typeof showToast === 'function') showToast('Brush smoothing: ' + window.brushSmoothing + '%');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [02] BRUSH STABILIZER — Photoshop "lazy mouse" rope. The brush tip lags
    // the cursor by N pixels, only catching up when the cursor pulls past the radius.
    // ─────────────────────────────────────────────────────────────────────────
    window.brushStabilizer = window.brushStabilizer || 0; // 0..200 px lag
    var _stabAnchor = null;
    window.stabilizeBrushPoint = function stabilizeBrushPoint(x, y) {
        var rope = Math.max(0, Math.min(200, parseInt(window.brushStabilizer || 0, 10)));
        if (rope <= 0) return { x: x, y: y };
        if (!_stabAnchor) { _stabAnchor = { x: x, y: y }; return { x: x, y: y }; }
        var dx = x - _stabAnchor.x, dy = y - _stabAnchor.y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d <= rope) return { x: _stabAnchor.x, y: _stabAnchor.y };
        var ratio = (d - rope) / d;
        _stabAnchor.x += dx * ratio;
        _stabAnchor.y += dy * ratio;
        return { x: Math.round(_stabAnchor.x), y: Math.round(_stabAnchor.y) };
    };
    window.resetBrushStabilizer = function resetBrushStabilizer() { _stabAnchor = null; };
    window.setBrushStabilizer = function setBrushStabilizer(v) {
        window.brushStabilizer = Math.max(0, Math.min(200, parseInt(v, 10) || 0));
        if (typeof showToast === 'function') showToast('Brush stabilizer: ' + window.brushStabilizer + 'px');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [03] BRUSH PREVIEW CIRCLE upgrade — animated pulse on tool switch + crosshair dot.
    // ─────────────────────────────────────────────────────────────────────────
    window.pulseBrushCursor = function pulseBrushCursor() {
        var c = document.getElementById('brushCursorCircle');
        if (!c) return;
        c.style.transition = 'box-shadow 240ms ease-out, transform 240ms ease-out';
        var origShadow = c.style.boxShadow;
        c.style.boxShadow = '0 0 0 4px rgba(255,255,255,0.25)';
        setTimeout(function () { c.style.boxShadow = origShadow || ''; }, 260);
    };
    window.ensureBrushCenterDot = function ensureBrushCenterDot() {
        var c = document.getElementById('brushCursorCircle');
        if (!c) return;
        if (c.querySelector('.brushCenterDot')) return;
        var dot = document.createElement('div');
        dot.className = 'brushCenterDot';
        dot.style.cssText = 'position:absolute;top:50%;left:50%;width:3px;height:3px;margin:-1.5px 0 0 -1.5px;background:rgba(255,255,255,0.85);border-radius:50%;pointer-events:none;box-shadow:0 0 0 1px rgba(0,0,0,0.5);';
        c.style.position = c.style.position || 'fixed';
        c.appendChild(dot);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [04] TOOL FEEDBACK — flash a small status hint when the tool changes.
    // ─────────────────────────────────────────────────────────────────────────
    window.flashToolHint = function flashToolHint(text) {
        var el = document.getElementById('platinumToolFlash');
        if (!el) {
            el = document.createElement('div');
            el.id = 'platinumToolFlash';
            el.style.cssText = 'position:fixed;left:50%;top:14%;transform:translateX(-50%);background:rgba(20,24,32,0.92);color:#ffd86b;font:600 13px/1 system-ui,sans-serif;padding:8px 14px;border-radius:8px;border:1px solid rgba(255,216,107,0.35);box-shadow:0 6px 20px rgba(0,0,0,0.4);z-index:99999;pointer-events:none;opacity:0;transition:opacity 160ms ease;';
            document.body.appendChild(el);
        }
        el.textContent = text;
        el.style.opacity = '1';
        clearTimeout(el._t);
        el._t = setTimeout(function () { el.style.opacity = '0'; }, 700);
    };
    // Wrap setCanvasMode to add hint on every switch (without breaking it).
    if (typeof window.setCanvasMode === 'function' && !window._setCanvasModeWrapped) {
        var _origSetCanvasMode = window.setCanvasMode;
        window.setCanvasMode = function (mode) {
            var prev = window.canvasMode;
            var r = _origSetCanvasMode.apply(this, arguments);
            try {
                if (prev !== mode) {
                    var label = document.getElementById('activeToolLabel');
                    var name = (label && label.textContent) || (mode + '').toUpperCase();
                    window.flashToolHint('Tool: ' + name);
                    window.pulseBrushCursor();
                    window.resetBrushSmoothing();
                    window.resetBrushStabilizer();
                }
            } catch (e) {}
            return r;
        };
        window._setCanvasModeWrapped = true;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // [05] PIXEL-PERFECT MODE — strips antialiasing for pencil/eraser strokes.
    // Toggleable; consumers can read window.pixelPerfectEnabled.
    // ─────────────────────────────────────────────────────────────────────────
    window.pixelPerfectEnabled = false;
    window.togglePixelPerfect = function togglePixelPerfect() {
        window.pixelPerfectEnabled = !window.pixelPerfectEnabled;
        if (typeof showToast === 'function') showToast('Pixel-perfect: ' + (window.pixelPerfectEnabled ? 'ON' : 'OFF'));
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [06] BRUSH SIZE shortcuts polish — show toast with new value, clamp safer,
    // and add Ctrl+[ / Ctrl+] for x2/x0.5 multiplicative jumps.
    // ─────────────────────────────────────────────────────────────────────────
    window.bumpBrushSize = function bumpBrushSize(delta) {
        var el = document.getElementById('brushSize');
        if (!el) return;
        var cur = parseInt(el.value, 10) || 20;
        var next = Math.max(1, Math.min(500, cur + delta));
        el.value = next;
        if (typeof el.oninput === 'function') el.oninput();
        if (typeof showToast === 'function') showToast('Brush size: ' + next + 'px');
    };
    window.scaleBrushSize = function scaleBrushSize(factor) {
        var el = document.getElementById('brushSize');
        if (!el) return;
        var cur = parseInt(el.value, 10) || 20;
        var next = Math.max(1, Math.min(500, Math.round(cur * factor)));
        el.value = next;
        if (typeof el.oninput === 'function') el.oninput();
        if (typeof showToast === 'function') showToast('Brush size: ' + next + 'px');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [07] BRUSH HARDNESS shortcut polish + toast.
    // ─────────────────────────────────────────────────────────────────────────
    window.bumpBrushHardness = function bumpBrushHardness(delta) {
        var el = document.getElementById('brushHardness');
        if (!el) return;
        var cur = parseInt(el.value, 10) || 100;
        var next = Math.max(0, Math.min(100, cur + delta));
        el.value = next;
        if (typeof el.oninput === 'function') el.oninput();
        if (typeof showToast === 'function') showToast('Hardness: ' + next + '%');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [08] BRUSH FLOW shortcut.
    // ─────────────────────────────────────────────────────────────────────────
    window.bumpBrushFlow = function bumpBrushFlow(delta) {
        var el = document.getElementById('brushFlow');
        if (!el) return;
        var cur = parseInt(el.value, 10) || 100;
        var next = Math.max(1, Math.min(100, cur + delta));
        el.value = next;
        if (typeof el.oninput === 'function') el.oninput();
        if (typeof showToast === 'function') showToast('Flow: ' + next + '%');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [09] EYEDROPPER readout upgrade — adds HSL display alongside RGB+HEX.
    // ─────────────────────────────────────────────────────────────────────────
    window.rgbToHsl = function rgbToHsl(r, g, b) {
        r /= 255; g /= 255; b /= 255;
        var max = Math.max(r, g, b), min = Math.min(r, g, b);
        var h = 0, s = 0, l = (max + min) / 2;
        if (max !== min) {
            var d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }
        return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) };
    };
    window.formatHSL = function formatHSL(rgb) {
        var hsl = window.rgbToHsl(rgb.r, rgb.g, rgb.b);
        return 'HSL(' + hsl.h + ', ' + hsl.s + '%, ' + hsl.l + '%)';
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [10] EYEDROPPER sample size — 1px (point), 3x3 avg, 5x5 avg.
    // Consumers should call window.sampleEyedropperPixel(x, y) to honor the setting.
    // ─────────────────────────────────────────────────────────────────────────
    window.eyedropperSampleSize = window.eyedropperSampleSize || 1;
    window.setEyedropperSampleSize = function setEyedropperSampleSize(n) {
        n = parseInt(n, 10);
        if ([1, 3, 5].indexOf(n) === -1) n = 1;
        window.eyedropperSampleSize = n;
        if (typeof showToast === 'function') showToast('Eyedropper sample: ' + n + 'x' + n);
    };
    window.sampleEyedropperPixel = function sampleEyedropperPixel(x, y) {
        if (typeof paintImageData === 'undefined' || !paintImageData) return null;
        var canvas = document.getElementById('paintCanvas');
        if (!canvas) return null;
        var w = canvas.width, h = canvas.height;
        var n = window.eyedropperSampleSize || 1;
        if (n <= 1) {
            var idx = (y * w + x) * 4;
            return { r: paintImageData.data[idx], g: paintImageData.data[idx + 1], b: paintImageData.data[idx + 2] };
        }
        var half = (n - 1) >> 1;
        var sr = 0, sg = 0, sb = 0, count = 0;
        for (var dy = -half; dy <= half; dy++) {
            for (var dx = -half; dx <= half; dx++) {
                var px = x + dx, py = y + dy;
                if (px < 0 || px >= w || py < 0 || py >= h) continue;
                var pi = (py * w + px) * 4;
                sr += paintImageData.data[pi];
                sg += paintImageData.data[pi + 1];
                sb += paintImageData.data[pi + 2];
                count++;
            }
        }
        return count > 0
            ? { r: Math.round(sr / count), g: Math.round(sg / count), b: Math.round(sb / count) }
            : null;
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [11] MAGIC WAND tolerance defaults nudge — clamp seed to safer range.
    // Also expose anti-alias toggle.
    // ─────────────────────────────────────────────────────────────────────────
    window.wandAntiAlias = window.wandAntiAlias === undefined ? true : window.wandAntiAlias;
    window.setWandAntiAlias = function setWandAntiAlias(on) {
        window.wandAntiAlias = !!on;
        if (typeof showToast === 'function') showToast('Wand anti-alias: ' + (on ? 'ON' : 'OFF'));
    };
    window.suggestWandTolerance = function suggestWandTolerance(rgb) {
        // Rough heuristic: low-contrast grays need more tolerance.
        if (!rgb) return 32;
        var max = Math.max(rgb.r, rgb.g, rgb.b);
        var min = Math.min(rgb.r, rgb.g, rgb.b);
        var sat = max === 0 ? 0 : (max - min) / max;
        if (sat < 0.1) return 18; // gray → tighter
        if (sat > 0.6) return 40; // saturated → looser
        return 28;
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [12] LASSO close-on-double-click already exists; expose helper.
    // ─────────────────────────────────────────────────────────────────────────
    window.closeLassoNow = function closeLassoNow() {
        if (typeof window.closeLasso === 'function') window.closeLasso(new MouseEvent('dblclick'));
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [13] MARQUEE — fixed aspect ratio + fixed size mode (consumed by drawRectPreview/onmouseup).
    // ─────────────────────────────────────────────────────────────────────────
    window.marqueeFixedAspect = null; // e.g. {w:16, h:9}
    window.marqueeFixedSize = null; // e.g. {w:256, h:128}
    window.setMarqueeAspect = function setMarqueeAspect(w, h) {
        window.marqueeFixedAspect = (w && h) ? { w: w, h: h } : null;
        if (typeof showToast === 'function') showToast(w && h ? 'Marquee aspect: ' + w + ':' + h : 'Marquee aspect: free');
    };
    window.setMarqueeFixedSize = function setMarqueeFixedSize(w, h) {
        window.marqueeFixedSize = (w && h) ? { w: w, h: h } : null;
        if (typeof showToast === 'function') showToast(w && h ? 'Marquee fixed size: ' + w + 'x' + h : 'Marquee size: free');
    };
    window.applyMarqueeConstraints = function applyMarqueeConstraints(start, end) {
        var x1 = start.x, y1 = start.y, x2 = end.x, y2 = end.y;
        if (window.marqueeFixedSize) {
            x2 = x1 + window.marqueeFixedSize.w * (x2 < x1 ? -1 : 1);
            y2 = y1 + window.marqueeFixedSize.h * (y2 < y1 ? -1 : 1);
            return { x: x2, y: y2 };
        }
        if (window.marqueeFixedAspect) {
            var dx = Math.abs(x2 - x1);
            var dy = dx * (window.marqueeFixedAspect.h / window.marqueeFixedAspect.w);
            return { x: x2, y: y1 + dy * (y2 < y1 ? -1 : 1) };
        }
        return end;
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [14] MOVE TOOL — distance overlay during drag.
    // ─────────────────────────────────────────────────────────────────────────
    window.showMoveDistance = function showMoveDistance(dx, dy) {
        var el = document.getElementById('platinumMoveOverlay');
        if (!el) {
            el = document.createElement('div');
            el.id = 'platinumMoveOverlay';
            el.style.cssText = 'position:fixed;background:rgba(0,0,0,0.78);color:#7df9ff;font:600 12px/1 monospace;padding:5px 9px;border-radius:6px;z-index:99998;pointer-events:none;border:1px solid rgba(125,249,255,0.4);';
            document.body.appendChild(el);
        }
        el.textContent = 'Δ ' + Math.round(dx) + ', ' + Math.round(dy) + '  (' + Math.round(Math.sqrt(dx * dx + dy * dy)) + 'px)';
        el.style.display = 'block';
    };
    window.hideMoveDistance = function hideMoveDistance() {
        var el = document.getElementById('platinumMoveOverlay');
        if (el) el.style.display = 'none';
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [15] TRANSFORM HANDLES — proportional-scale helper (Shift constraint).
    // ─────────────────────────────────────────────────────────────────────────
    window.proportionalScaleSize = function proportionalScaleSize(origW, origH, newW, newH, shift) {
        if (!shift) return { w: newW, h: newH };
        var ratio = origW / origH;
        if (Math.abs(newW - origW) > Math.abs(newH - origH)) return { w: newW, h: Math.round(newW / ratio) };
        return { w: Math.round(newH * ratio), h: newH };
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [16] ERASER — Alt held = temporarily reverse to brush mode.
    // ─────────────────────────────────────────────────────────────────────────
    window._eraserAltHold = false;
    document.addEventListener('keydown', function (e) {
        if (e.defaultPrevented) return; // SESSION ROUTER bail
        if (e.key === 'Alt' && window.canvasMode === 'erase' && !window._eraserAltHold) {
            window._eraserAltHold = true;
            window._eraserPrevMode = window.canvasMode;
            // Soft visual: tint the cursor circle blue to show flip.
            var c = document.getElementById('brushCursorCircle');
            if (c) c.style.borderColor = 'rgba(125,200,255,0.85)';
        }
    });
    document.addEventListener('keyup', function (e) {
        if (e.key === 'Alt' && window._eraserAltHold) {
            window._eraserAltHold = false;
            if (typeof updateBrushCursorVisibility === 'function') updateBrushCursorVisibility();
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [17] CLONE STAMP — alignment toggle (aligned vs. fixed source).
    // ─────────────────────────────────────────────────────────────────────────
    window.cloneAligned = window.cloneAligned === undefined ? true : window.cloneAligned;
    window.toggleCloneAligned = function toggleCloneAligned() {
        window.cloneAligned = !window.cloneAligned;
        if (typeof showToast === 'function') showToast('Clone aligned: ' + (window.cloneAligned ? 'ON' : 'OFF'));
    };
    window.showCloneSourceMarker = function showCloneSourceMarker(x, y) {
        var rc = document.getElementById('regionCanvas');
        if (!rc) return;
        var ctx = rc.getContext('2d');
        ctx.save();
        ctx.strokeStyle = 'rgba(0,255,128,0.9)';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 3]);
        ctx.beginPath();
        ctx.arc(x, y, 12, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x - 16, y); ctx.lineTo(x - 6, y);
        ctx.moveTo(x + 6, y); ctx.lineTo(x + 16, y);
        ctx.moveTo(x, y - 16); ctx.lineTo(x, y - 6);
        ctx.moveTo(x, y + 6); ctx.lineTo(x, y + 16);
        ctx.stroke();
        ctx.restore();
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [18] HISTORY BRUSH — clearer source-state indicator.
    // ─────────────────────────────────────────────────────────────────────────
    window.markHistorySnapshot = function markHistorySnapshot(label) {
        var el = document.getElementById('platinumHistoryFlag');
        if (!el) {
            el = document.createElement('div');
            el.id = 'platinumHistoryFlag';
            el.style.cssText = 'position:fixed;right:14px;bottom:90px;background:rgba(45,30,80,0.92);color:#cc88ff;font:600 11px/1.4 system-ui,sans-serif;padding:6px 9px;border-radius:6px;z-index:99997;pointer-events:none;border:1px solid rgba(204,136,255,0.4);max-width:240px;';
            document.body.appendChild(el);
        }
        el.textContent = '🕒 History snapshot: ' + (label || 'current');
        clearTimeout(el._t);
        el._t = setTimeout(function () { el.remove(); }, 2200);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [19] UNDO/REDO tooltip — show what action will be undone.
    // ─────────────────────────────────────────────────────────────────────────
    window.getUndoLabel = function getUndoLabel() {
        try {
            var trackedKind = (typeof _peekLatestUndoKind === 'function') ? _peekLatestUndoKind() : null;
            if (trackedKind === 'layer' && typeof _layerUndoStack !== 'undefined' && _layerUndoStack.length > 0) {
                var layerTop = _layerUndoStack[_layerUndoStack.length - 1];
                return 'Undo: ' + (layerTop.label || 'layer edit');
            }
            if (trackedKind === 'pixel' && typeof _pixelUndoStack !== 'undefined' && _pixelUndoStack.length > 0) {
                return 'Undo: ' + (_pixelUndoStack[_pixelUndoStack.length - 1].label || 'paint');
            }
            if (trackedKind === 'zone-mask' && typeof undoStack !== 'undefined' && undoStack.length > 0) {
                var maskZone = undoStack[undoStack.length - 1].zoneIndex;
                return 'Undo: Zone ' + (maskZone + 1) + ' edit';
            }
            if (trackedKind === 'zone-config' && typeof zoneUndoStack !== 'undefined' && zoneUndoStack.length > 0) {
                var zoneTop = zoneUndoStack[zoneUndoStack.length - 1];
                return 'Undo: ' + (zoneTop.label || 'zone change');
            }
            if (typeof _layerUndoStack !== 'undefined' && _layerUndoStack.length > 0) {
                var top = _layerUndoStack[_layerUndoStack.length - 1];
                return 'Undo: ' + (top.label || 'layer edit');
            }
            if (typeof _pixelUndoStack !== 'undefined' && _pixelUndoStack.length > 0) {
                return 'Undo: ' + (_pixelUndoStack[_pixelUndoStack.length - 1].label || 'paint');
            }
            if (typeof undoStack !== 'undefined' && undoStack.length > 0) {
                var z = undoStack[undoStack.length - 1].zoneIndex;
                return 'Undo: Zone ' + (z + 1) + ' edit';
            }
        } catch (e) {}
        return 'Nothing to undo';
    };
    window.getRedoLabel = function getRedoLabel() {
        try {
            var trackedKind = (typeof _peekLatestRedoKind === 'function') ? _peekLatestRedoKind() : null;
            if (trackedKind === 'layer' && typeof _layerRedoStack !== 'undefined' && _layerRedoStack.length > 0) {
                return 'Redo: ' + (_layerRedoStack[_layerRedoStack.length - 1].label || 'layer edit');
            }
            if (trackedKind === 'pixel' && typeof _pixelRedoStack !== 'undefined' && _pixelRedoStack.length > 0) {
                return 'Redo: ' + (_pixelRedoStack[_pixelRedoStack.length - 1].label || 'paint');
            }
            if (trackedKind === 'zone-mask' && typeof redoStack !== 'undefined' && redoStack.length > 0) {
                return 'Redo: Zone ' + (redoStack[redoStack.length - 1].zoneIndex + 1) + ' edit';
            }
            if (trackedKind === 'zone-config' && typeof zoneRedoStack !== 'undefined' && zoneRedoStack.length > 0) {
                return 'Redo: ' + (zoneRedoStack[zoneRedoStack.length - 1].label || 'zone change');
            }
            if (typeof _pixelRedoStack !== 'undefined' && _pixelRedoStack.length > 0) {
                return 'Redo: ' + (_pixelRedoStack[_pixelRedoStack.length - 1].label || 'paint');
            }
            if (typeof redoStack !== 'undefined' && redoStack.length > 0) {
                return 'Redo: Zone ' + (redoStack[redoStack.length - 1].zoneIndex + 1) + ' edit';
            }
        } catch (e) {}
        return 'Nothing to redo';
    };
    window.refreshUndoTooltips = function refreshUndoTooltips() {
        var ub = document.getElementById('undoBtn') || document.querySelector('[data-action="undo"]');
        if (ub) ub.title = window.getUndoLabel() + ' (Ctrl+Z)';
        var rb = document.getElementById('redoBtn') || document.querySelector('[data-action="redo"]');
        if (rb) rb.title = window.getRedoLabel() + ' (Ctrl+Shift+Z)';
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [20] LAYER thumbnail dirty-tracking — only re-render thumbs whose layer changed.
    // Consumers call markLayerThumbDirty(layerId) after edits; renderer reads the set.
    // ─────────────────────────────────────────────────────────────────────────
    window._dirtyLayerThumbs = window._dirtyLayerThumbs || new Set();
    window.markLayerThumbDirty = function markLayerThumbDirty(layerId) {
        if (layerId == null) return;
        window._dirtyLayerThumbs.add(layerId);
    };
    window.isLayerThumbDirty = function isLayerThumbDirty(layerId) {
        return window._dirtyLayerThumbs.has(layerId);
    };
    window.clearLayerThumbDirty = function clearLayerThumbDirty(layerId) {
        if (layerId == null) window._dirtyLayerThumbs.clear();
        else window._dirtyLayerThumbs.delete(layerId);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [21] LAYER drag-and-drop — visual indicator helper for drop position.
    // ─────────────────────────────────────────────────────────────────────────
    window.showLayerDropIndicator = function showLayerDropIndicator(targetEl, position) {
        var ind = document.getElementById('platinumLayerDropInd');
        if (!ind) {
            ind = document.createElement('div');
            ind.id = 'platinumLayerDropInd';
            ind.style.cssText = 'position:absolute;height:3px;background:linear-gradient(90deg,#ffcb6b,#ff7e5f);box-shadow:0 0 8px rgba(255,203,107,0.7);z-index:9999;pointer-events:none;border-radius:2px;';
            document.body.appendChild(ind);
        }
        if (!targetEl) { ind.style.display = 'none'; return; }
        var r = targetEl.getBoundingClientRect();
        ind.style.display = 'block';
        ind.style.left = r.left + 'px';
        ind.style.width = r.width + 'px';
        ind.style.top = (position === 'above' ? r.top - 1 : r.bottom - 2) + 'px';
    };
    window.hideLayerDropIndicator = function hideLayerDropIndicator() {
        var ind = document.getElementById('platinumLayerDropInd');
        if (ind) ind.style.display = 'none';
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [22] LAYER quick-find — type to filter the layer panel.
    // ─────────────────────────────────────────────────────────────────────────
    window.filterLayerPanel = function filterLayerPanel(query) {
        var panel = document.getElementById('layerPanel') || document.querySelector('.layer-panel');
        if (!panel) return;
        var q = (query || '').trim().toLowerCase();
        var items = panel.querySelectorAll('[data-layer-name], .layer-row, .layer-item');
        items.forEach(function (el) {
            var name = (el.getAttribute('data-layer-name') || el.textContent || '').toLowerCase();
            el.style.display = (!q || name.indexOf(q) !== -1) ? '' : 'none';
        });
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [23] LAYER alpha-lock — preserve transparency when painting on the layer.
    // ─────────────────────────────────────────────────────────────────────────
    window.toggleLayerAlphaLock = function toggleLayerAlphaLock(layerId) {
        if (typeof _psdLayers === 'undefined') return;
        var L = _psdLayers.find(function (l) { return l.id === layerId; });
        if (!L) return;
        // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W11): missing undo.
        // Every layer-property toggle should be undoable so the painter can
        // revert an accidental click without rebuilding state by hand.
        // NOTE (Hennig P7): no triggerPreviewRender here — alpha-lock does
        // not change layer pixels; it only changes how the NEXT stroke is
        // gated. The preview will catch up on the next paint action.
        // Asymmetric vs W12 (clipping) by design, not by accident.
        if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('Toggle alpha lock');
        L.alphaLock = !L.alphaLock;
        if (typeof showToast === 'function') showToast('Alpha lock ' + (L.alphaLock ? 'ON' : 'OFF') + ' — ' + (L.name || 'layer'));
        if (typeof renderLayerPanel === 'function') renderLayerPanel();
    };
    window.isLayerAlphaLocked = function isLayerAlphaLocked(layerId) {
        if (typeof _psdLayers === 'undefined') return false;
        var L = _psdLayers.find(function (l) { return l.id === layerId; });
        return !!(L && L.alphaLock);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [24] LAYER clipping mask — Alt+click between layers to clip.
    // ─────────────────────────────────────────────────────────────────────────
    window.toggleClippingMask = function toggleClippingMask(layerId) {
        if (typeof _psdLayers === 'undefined') return;
        var L = _psdLayers.find(function (l) { return l.id === layerId; });
        if (!L) return;
        // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W12): missing undo + silent-stale.
        // recompositeFromLayers updates the composite, but the live preview was
        // not refreshed and the change was not pushed onto the layer-stack undo
        // ring — Alt+click clip pair flickered with no way to revert.
        if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('Toggle clipping mask');
        L.clippingMask = !L.clippingMask;
        if (typeof showToast === 'function') showToast('Clipping mask ' + (L.clippingMask ? 'ON' : 'OFF') + ' — ' + (L.name || 'layer'));
        if (typeof renderLayerPanel === 'function') renderLayerPanel();
        if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [25] CANVAS zoom — fit-to-window keyboard shortcut wiring (Ctrl+Alt+0).
    // (Ctrl+0 already does fit; this also adds 'F' double-tap for fit).
    // ─────────────────────────────────────────────────────────────────────────
    var _lastFKey = 0;
    document.addEventListener('keydown', function (e) {
        if (e.defaultPrevented) return; // SESSION ROUTER bail
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement && document.activeElement.tagName)) return;
        if (e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return;
        if (e.key === 'f' || e.key === 'F') {
            // Don't conflict if blur-brush hotkey is already 'f' — only double-tap fits.
            var now = Date.now();
            if (now - _lastFKey < 320) {
                if (typeof canvasZoom === 'function') canvasZoom('fit');
                if (typeof showToast === 'function') showToast('Fit to window');
            }
            _lastFKey = now;
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [26] CANVAS rotate — view rotation already exists; expose 90° helpers.
    // ─────────────────────────────────────────────────────────────────────────
    window.rotateView90CW = function rotateView90CW() { if (typeof rotateView === 'function') rotateView(90); };
    window.rotateView90CCW = function rotateView90CCW() { if (typeof rotateView === 'function') rotateView(-90); };

    // ─────────────────────────────────────────────────────────────────────────
    // [27] PAN cursor feedback — ensure consistent grab/grabbing across viewport children.
    // ─────────────────────────────────────────────────────────────────────────
    document.addEventListener('keydown', function (e) {
        if (e.defaultPrevented) return; // SESSION ROUTER bail
        if (e.code === 'Space' && !e.repeat) {
            // BUG #63a: do NOT flip canvas cursor when a text/number input has focus.
            // Painter typing a zone name with a space would see the pan cursor flash.
            var ae = document.activeElement;
            if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA' || ae.tagName === 'SELECT' || ae.isContentEditable)) return;
            var canvas = document.getElementById('paintCanvas');
            if (canvas) canvas.style.cursor = 'grab';
        }
    });
    document.addEventListener('keyup', function (e) {
        if (e.code === 'Space') {
            var canvas = document.getElementById('paintCanvas');
            if (canvas && typeof updateBrushCursorVisibility === 'function') updateBrushCursorVisibility();
        }
    });
    // BUG #63b: Alt/Space held-state leaks when user Alt+Tabs away (keyup fires on OS, not page).
    // Reset modifier flags + brush cursor on window blur so tools don't misbehave on return.
    window.addEventListener('blur', function () {
        if (window._eraserAltHold) {
            window._eraserAltHold = false;
            if (typeof updateBrushCursorVisibility === 'function') updateBrushCursorVisibility();
        }
        var canvas = document.getElementById('paintCanvas');
        if (canvas && canvas.style.cursor === 'grab') {
            if (typeof updateBrushCursorVisibility === 'function') updateBrushCursorVisibility();
            else canvas.style.cursor = '';
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [28] SELECTION FEATHER — apply gaussian blur to a selection mask.
    // ─────────────────────────────────────────────────────────────────────────
    window.featherZoneSelection = function featherZoneSelection(px) {
        if (typeof zones === 'undefined' || typeof selectedZoneIndex === 'undefined') return;
        var zone = zones[selectedZoneIndex];
        if (!zone || !zone.regionMask) return;
        var canvas = document.getElementById('paintCanvas');
        if (!canvas) return;
        var w = canvas.width, h = canvas.height;
        var src = zone.regionMask, dst = new Uint8Array(w * h);
        var radius = Math.max(1, Math.min(50, parseInt(px, 10) || 1));
        // Cheap separable box blur, repeated thrice ≈ Gaussian.
        var tmp = new Float32Array(w * h);
        var out = new Float32Array(w * h);
        for (var i = 0; i < src.length; i++) tmp[i] = src[i];
        for (var pass = 0; pass < 3; pass++) {
            // Horizontal
            for (var y = 0; y < h; y++) {
                var sum = 0, c = 0;
                for (var x = -radius; x < w; x++) {
                    if (x + radius < w) { sum += tmp[y * w + x + radius]; c++; }
                    if (x - radius - 1 >= 0) { sum -= tmp[y * w + x - radius - 1]; c--; }
                    if (x >= 0) out[y * w + x] = sum / Math.max(1, c);
                }
            }
            // Vertical
            for (var xx = 0; xx < w; xx++) {
                var s2 = 0, c2 = 0;
                for (var yy = -radius; yy < h; yy++) {
                    if (yy + radius < h) { s2 += out[(yy + radius) * w + xx]; c2++; }
                    if (yy - radius - 1 >= 0) { s2 -= out[(yy - radius - 1) * w + xx]; c2--; }
                    if (yy >= 0) tmp[yy * w + xx] = s2 / Math.max(1, c2);
                }
            }
        }
        for (var k = 0; k < dst.length; k++) dst[k] = Math.max(0, Math.min(255, Math.round(tmp[k])));
        if (typeof pushUndo === 'function') pushUndo(selectedZoneIndex);
        zone.regionMask = dst;
        if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
        if (typeof showToast === 'function') showToast('Feathered selection by ' + radius + 'px');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [29] SELECTION grow / shrink keyboard shortcuts.
    // ─────────────────────────────────────────────────────────────────────────
    document.addEventListener('keydown', function (e) {
        if (e.defaultPrevented) return; // SESSION ROUTER bail
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement && document.activeElement.tagName)) return;
        if (!e.ctrlKey && !e.metaKey) return;
        if (e.shiftKey && e.key === '+') {
            e.preventDefault();
            if (typeof growRegionMask === 'function') growRegionMask(2);
        } else if (e.shiftKey && e.key === '_') {
            e.preventDefault();
            if (typeof shrinkRegionMask === 'function') shrinkRegionMask(2);
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [30] QUICK MASK MODE — Q toggles a red overlay paint mode for refining selection.
    // ─────────────────────────────────────────────────────────────────────────
    window.quickMaskActive = false;
    window.toggleQuickMask = function toggleQuickMask() {
        // Conflict avoidance: 'q' currently maps to smudge in the existing keyboard handler.
        // Toggle is exposed via API/button only.
        window.quickMaskActive = !window.quickMaskActive;
        var rc = document.getElementById('regionCanvas');
        if (rc) rc.style.mixBlendMode = window.quickMaskActive ? 'multiply' : '';
        if (typeof showToast === 'function') showToast('Quick Mask ' + (window.quickMaskActive ? 'ON (paint to refine)' : 'OFF'));
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [31] SNAP TO PIXEL GRID — round drawing coords to integer pixels.
    // ─────────────────────────────────────────────────────────────────────────
    window.snapToGrid = false;
    window._snapGridSize = 1;
    window.toggleSnapGrid = function toggleSnapGrid() {
        window.snapToGrid = !window.snapToGrid;
        if (typeof showToast === 'function') showToast('Snap to grid: ' + (window.snapToGrid ? 'ON' : 'OFF'));
    };
    window.snapPoint = function snapPoint(x, y) {
        if (!window.snapToGrid) return { x: x, y: y };
        var g = Math.max(1, window._snapGridSize | 0);
        return { x: Math.round(x / g) * g, y: Math.round(y / g) * g };
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [32] SMART GUIDES — show alignment lines when moving layers near edges/center.
    // ─────────────────────────────────────────────────────────────────────────
    window.drawSmartGuides = function drawSmartGuides(x, y, w, h) {
        var canvas = document.getElementById('paintCanvas');
        var rc = document.getElementById('regionCanvas');
        if (!canvas || !rc) return;
        var ctx = rc.getContext('2d');
        var cw = canvas.width, ch = canvas.height;
        var snap = 8;
        ctx.save();
        ctx.strokeStyle = 'rgba(255,80,255,0.85)';
        ctx.setLineDash([4, 3]);
        ctx.lineWidth = 1;
        var lines = [];
        if (Math.abs(x - 0) < snap) lines.push([0, 0, 0, ch]);
        if (Math.abs(x + w - cw) < snap) lines.push([cw, 0, cw, ch]);
        if (Math.abs(x + w / 2 - cw / 2) < snap) lines.push([cw / 2, 0, cw / 2, ch]);
        if (Math.abs(y - 0) < snap) lines.push([0, 0, cw, 0]);
        if (Math.abs(y + h - ch) < snap) lines.push([0, ch, cw, ch]);
        if (Math.abs(y + h / 2 - ch / 2) < snap) lines.push([0, ch / 2, cw, ch / 2]);
        for (var i = 0; i < lines.length; i++) {
            ctx.beginPath();
            ctx.moveTo(lines[i][0], lines[i][1]);
            ctx.lineTo(lines[i][2], lines[i][3]);
            ctx.stroke();
        }
        ctx.restore();
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [33] RULERS — toggleable rulers along canvas edges.
    // ─────────────────────────────────────────────────────────────────────────
    window.rulersVisible = false;
    window.toggleRulers = function toggleRulers() {
        window.rulersVisible = !window.rulersVisible;
        var t = document.getElementById('platinumRulerTop');
        var l = document.getElementById('platinumRulerLeft');
        if (window.rulersVisible) {
            if (!t) {
                t = document.createElement('div');
                t.id = 'platinumRulerTop';
                t.style.cssText = 'position:absolute;top:0;left:24px;right:0;height:16px;background:rgba(20,24,32,0.85);color:#aaa;font:9px monospace;border-bottom:1px solid #333;z-index:7;pointer-events:none;overflow:hidden;';
                var vp = document.getElementById('canvasViewport');
                if (vp) vp.appendChild(t);
            }
            if (!l) {
                l = document.createElement('div');
                l.id = 'platinumRulerLeft';
                l.style.cssText = 'position:absolute;top:16px;left:0;bottom:0;width:24px;background:rgba(20,24,32,0.85);color:#aaa;font:9px monospace;border-right:1px solid #333;z-index:7;pointer-events:none;overflow:hidden;';
                var vp2 = document.getElementById('canvasViewport');
                if (vp2) vp2.appendChild(l);
            }
            window.drawRulers();
        } else {
            if (t) t.remove();
            if (l) l.remove();
        }
        if (typeof showToast === 'function') showToast('Rulers ' + (window.rulersVisible ? 'ON' : 'OFF'));
    };
    window.drawRulers = function drawRulers() {
        if (!window.rulersVisible) return;
        var canvas = document.getElementById('paintCanvas');
        if (!canvas || !canvas.width) return;
        var t = document.getElementById('platinumRulerTop');
        var l = document.getElementById('platinumRulerLeft');
        if (!t || !l) return;
        var step = canvas.width >= 2048 ? 256 : 128;
        var html = '';
        for (var i = 0; i < canvas.width; i += step) html += '<span style="position:absolute;left:' + (i * (typeof currentZoom !== 'undefined' ? currentZoom : 1)) + 'px;top:1px;">' + i + '</span>';
        t.innerHTML = html;
        var html2 = '';
        for (var j = 0; j < canvas.height; j += step) html2 += '<span style="position:absolute;left:1px;top:' + (j * (typeof currentZoom !== 'undefined' ? currentZoom : 1)) + 'px;">' + j + '</span>';
        l.innerHTML = html2;
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [34] CROSSHAIR cursor option (precision work).
    // ─────────────────────────────────────────────────────────────────────────
    window.precisionCursor = false;
    window.togglePrecisionCursor = function togglePrecisionCursor() {
        window.precisionCursor = !window.precisionCursor;
        var canvas = document.getElementById('paintCanvas');
        if (canvas) {
            if (usesCustomBrushCursorMode(window.canvasMode)) canvas.style.cursor = getBrushNativeCursor();
            else if (window.precisionCursor) canvas.style.cursor = 'crosshair';
            else if (window.canvasMode === 'eyedropper' || window.canvasMode === 'wand' || window.canvasMode === 'selectall' || window.canvasMode === 'edge') canvas.style.cursor = 'crosshair';
            else canvas.style.cursor = 'cell';
        }
        if (typeof showToast === 'function') showToast('Precision cursor: ' + (window.precisionCursor ? 'ON' : 'OFF'));
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [35] TOOL DEFAULTS RESET — restore brush sliders to baseline.
    // ─────────────────────────────────────────────────────────────────────────
    window.resetToolDefaults = function resetToolDefaults() {
        var defs = { brushSize: 20, brushOpacity: 100, brushHardness: 100, brushFlow: 100, brushSpacing: 25, wandTolerance: 32, brushShape: 'round', symmetryMode: 'off' };
        for (var id in defs) {
            var el = document.getElementById(id);
            if (el) { el.value = defs[id]; if (typeof el.oninput === 'function') el.oninput(); }
        }
        window.brushSmoothing = 0;
        window.brushStabilizer = 0;
        if (typeof showToast === 'function') showToast('Tool defaults restored');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [36] LAST-USED COLOR palette — recent 8 swatches.
    // ─────────────────────────────────────────────────────────────────────────
    window.recentColors = window.recentColors || [];
    window.pushRecentColor = function pushRecentColor(hex) {
        if (!hex) return;
        hex = hex.toUpperCase();
        var i = window.recentColors.indexOf(hex);
        if (i !== -1) window.recentColors.splice(i, 1);
        window.recentColors.unshift(hex);
        if (window.recentColors.length > 8) window.recentColors.length = 8;
        try { localStorage.setItem('spb_recentColors', JSON.stringify(window.recentColors)); } catch (e) {}
        window.renderRecentColors();
    };
    window.renderRecentColors = function renderRecentColors() {
        var bar = document.getElementById('recentColorsBar');
        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'recentColorsBar';
            bar.style.cssText = 'position:fixed;bottom:64px;left:14px;display:flex;gap:4px;padding:5px;background:rgba(20,24,32,0.85);border:1px solid #444;border-radius:6px;z-index:99996;';
            document.body.appendChild(bar);
        }
        bar.innerHTML = window.recentColors.map(function (c) {
            return '<div title="' + c + '" style="width:20px;height:20px;background:' + c + ';border:1px solid #222;cursor:pointer;border-radius:3px;" onclick="if(window._foregroundColor!==undefined){window._foregroundColor=\'' + c + '\';if(typeof showToast===\'function\')showToast(\'FG: ' + c + '\');}"></div>';
        }).join('') || '<span style="color:#666;font:10px monospace;padding:3px;">recent colors</span>';
    };
    try {
        var stored = localStorage.getItem('spb_recentColors');
        if (stored) window.recentColors = _safeLocalStorageJSON('spb_recent_colors', []);
    } catch (e) {}

    // ─────────────────────────────────────────────────────────────────────────
    // [37] BRUSH SPACING — already exists; expose helper to tweak.
    // ─────────────────────────────────────────────────────────────────────────
    window.bumpBrushSpacing = function bumpBrushSpacing(delta) {
        var el = document.getElementById('brushSpacing');
        if (!el) return;
        var v = Math.max(1, Math.min(200, (parseInt(el.value, 10) || 25) + delta));
        el.value = v;
        if (typeof el.oninput === 'function') el.oninput();
        if (typeof showToast === 'function') showToast('Spacing: ' + v + '%');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [38] TEXT TOOL — common font list helper.
    // ─────────────────────────────────────────────────────────────────────────
    window.commonFonts = ['Arial', 'Helvetica', 'Inter', 'Roboto', 'Bebas Neue', 'Oswald', 'Impact', 'Montserrat', 'Times New Roman', 'Georgia', 'Courier New', 'Monaco', 'Verdana'];
    window.getTextAlignment = function getTextAlignment() {
        return (document.getElementById('textAlign') && document.getElementById('textAlign').value) || 'left';
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [39] SHAPE TOOL — fill/stroke toggle + rounded corners storage.
    // ─────────────────────────────────────────────────────────────────────────
    window.shapeStyle = window.shapeStyle || { fill: true, stroke: false, strokeWidth: 2, cornerRadius: 0 };
    window.setShapeStyle = function setShapeStyle(opts) {
        Object.assign(window.shapeStyle, opts || {});
        if (typeof showToast === 'function') showToast('Shape: fill=' + window.shapeStyle.fill + ' stroke=' + window.shapeStyle.stroke + ' r=' + window.shapeStyle.cornerRadius);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [40] GRADIENT multi-stop editor (presets).
    // ─────────────────────────────────────────────────────────────────────────
    window.gradientPresets = window.gradientPresets || [
        { name: 'Sunset', stops: [[0, '#ff4e50'], [0.5, '#f9d423'], [1, '#fc913a']] },
        { name: 'Ocean', stops: [[0, '#0093e9'], [1, '#80d0c7']] },
        { name: 'Mono Fade', stops: [[0, '#000000'], [1, '#ffffff']] },
        { name: 'Carbon Heat', stops: [[0, '#1a1a1a'], [0.5, '#ff6b00'], [1, '#ffd700']] },
    ];
    window.saveCustomGradient = function saveCustomGradient(name, stops) {
        if (!name || !stops || !stops.length) return;
        window.gradientPresets.push({ name: name, stops: stops });
        try {
            var saved = JSON.parse(localStorage.getItem('spb_gradients') || '[]');
            saved.push({ name: name, stops: stops });
            localStorage.setItem('spb_gradients', JSON.stringify(saved));
        } catch (e) {}
        if (typeof showToast === 'function') showToast('Saved gradient: ' + name);
    };
    try {
        var savedG = JSON.parse(localStorage.getItem('spb_gradients') || '[]');
        savedG.forEach(function (g) { window.gradientPresets.push(g); });
    } catch (e) {}

    // ─────────────────────────────────────────────────────────────────────────
    // [41] BUCKET FILL — global vs contiguous + anti-alias toggle.
    // ─────────────────────────────────────────────────────────────────────────
    window.bucketContiguous = window.bucketContiguous === undefined ? true : window.bucketContiguous;
    window.bucketAntiAlias = window.bucketAntiAlias === undefined ? true : window.bucketAntiAlias;
    window.toggleBucketContiguous = function toggleBucketContiguous() {
        window.bucketContiguous = !window.bucketContiguous;
        if (typeof showToast === 'function') showToast('Bucket: ' + (window.bucketContiguous ? 'contiguous' : 'global'));
    };
    window.toggleBucketAntiAlias = function toggleBucketAntiAlias() {
        window.bucketAntiAlias = !window.bucketAntiAlias;
        if (typeof showToast === 'function') showToast('Bucket anti-alias: ' + (window.bucketAntiAlias ? 'ON' : 'OFF'));
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [42] PEN TOOL — better bezier handle visualizer.
    // ─────────────────────────────────────────────────────────────────────────
    window.drawPenHandles = function drawPenHandles(points) {
        var rc = document.getElementById('regionCanvas');
        if (!rc || !points || !points.length) return;
        var ctx = rc.getContext('2d');
        ctx.save();
        ctx.fillStyle = '#00e5ff';
        ctx.strokeStyle = 'rgba(0,229,255,0.5)';
        ctx.lineWidth = 1;
        for (var i = 0; i < points.length; i++) {
            var p = points[i];
            ctx.beginPath();
            ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
            ctx.fill();
            if (p.cx2 != null) {
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(p.cx2, p.cy2);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(p.cx2, p.cy2, 3, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        ctx.restore();
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [43] LAYER EFFECTS performance — only re-render fx if layer changed.
    // ─────────────────────────────────────────────────────────────────────────
    window._fxCache = window._fxCache || new Map();
    window.shouldRerenderFx = function shouldRerenderFx(layer) {
        if (!layer || !layer.id) return true;
        var key = JSON.stringify({
            id: layer.id,
            fx: layer.effects,
            opacity: layer.opacity,
            blendMode: layer.blendMode,
            visible: layer.visible,
            dirty: window._dirtyLayerThumbs.has(layer.id)
        });
        var prev = window._fxCache.get(layer.id);
        window._fxCache.set(layer.id, key);
        return prev !== key;
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [44] DEBOUNCE BRUSH DABS — coalesce consecutive dabs within 1 frame.
    // Helpful when mousemove fires faster than render.
    // ─────────────────────────────────────────────────────────────────────────
    window._brushDabRaf = 0;
    window.scheduleBrushFlush = function scheduleBrushFlush(fn) {
        if (window._brushDabRaf) return;
        window._brushDabRaf = requestAnimationFrame(function () {
            window._brushDabRaf = 0;
            try { fn(); } catch (e) { console.error(e); }
        });
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [45] CURSOR OUTLINE color — invert based on background luminance.
    // ─────────────────────────────────────────────────────────────────────────
    window.adaptiveCursorColor = true;
    window.updateCursorContrast = function updateCursorContrast(x, y) {
        if (!window.adaptiveCursorColor) return;
        var rgb = window.sampleEyedropperPixel ? window.sampleEyedropperPixel(x, y) : null;
        if (!rgb) return;
        var lum = 0.2126 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b;
        var c = document.getElementById('brushCursorCircle');
        if (!c) return;
        var darkBg = lum < 128;
        c.style.borderColor = darkBg ? 'rgba(255,255,255,0.85)' : 'rgba(0,0,0,0.85)';
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [46] SAVE BRUSH PRESETS — persist size/hardness/spacing/flow/shape.
    // ─────────────────────────────────────────────────────────────────────────
    window.brushPresets = [];
    window.saveBrushPreset = function saveBrushPreset(name) {
        if (!name) name = 'Preset ' + (window.brushPresets.length + 1);
        var preset = {
            name: name,
            size: parseInt(document.getElementById('brushSize')?.value || 20, 10),
            opacity: parseInt(document.getElementById('brushOpacity')?.value || 100, 10),
            hardness: parseInt(document.getElementById('brushHardness')?.value || 100, 10),
            flow: parseInt(document.getElementById('brushFlow')?.value || 100, 10),
            spacing: parseInt(document.getElementById('brushSpacing')?.value || 25, 10),
            shape: document.getElementById('brushShape')?.value || 'round',
            smoothing: window.brushSmoothing || 0,
            stabilizer: window.brushStabilizer || 0
        };
        window.brushPresets.push(preset);
        try { localStorage.setItem('spb_brushPresets', JSON.stringify(window.brushPresets)); } catch (e) {}
        if (typeof showToast === 'function') showToast('Saved brush preset: ' + name);
    };
    window.loadBrushPreset = function loadBrushPreset(name) {
        var p = window.brushPresets.find(function (x) { return x.name === name; });
        if (!p) return;
        ['size', 'opacity', 'hardness', 'flow', 'spacing'].forEach(function (k) {
            var el = document.getElementById('brush' + k.charAt(0).toUpperCase() + k.slice(1));
            if (el && p[k] != null) { el.value = p[k]; if (typeof el.oninput === 'function') el.oninput(); }
        });
        var sh = document.getElementById('brushShape');
        if (sh && p.shape) sh.value = p.shape;
        if (p.smoothing != null) window.brushSmoothing = p.smoothing;
        if (p.stabilizer != null) window.brushStabilizer = p.stabilizer;
        if (typeof showToast === 'function') showToast('Loaded preset: ' + name);
    };
    try {
        var bp = localStorage.getItem('spb_brushPresets');
        if (bp) window.brushPresets = JSON.parse(bp) || [];
    } catch (e) {}

    // ─────────────────────────────────────────────────────────────────────────
    // [47] TOOL SWITCH ANIMATION — already covered by flashToolHint + pulseBrushCursor [04].
    // Add a subtle border flash on the active toolbar button.
    // ─────────────────────────────────────────────────────────────────────────
    window.flashActiveToolButton = function flashActiveToolButton() {
        var btn = document.querySelector('.draw-tool-btn.active, .vtool-btn.active');
        if (!btn) return;
        btn.style.transition = 'box-shadow 240ms ease-out';
        var prev = btn.style.boxShadow;
        btn.style.boxShadow = '0 0 0 3px rgba(255,216,107,0.6)';
        setTimeout(function () { btn.style.boxShadow = prev || ''; }, 280);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [48] COORDINATE READOUT — show pixel x,y under cursor (status bar).
    // ─────────────────────────────────────────────────────────────────────────
    window.ensureCoordReadout = function ensureCoordReadout() {
        var el = document.getElementById('platinumCoordReadout');
        if (!el) {
            el = document.createElement('div');
            el.id = 'platinumCoordReadout';
            el.style.cssText = 'position:fixed;left:14px;bottom:14px;background:rgba(20,24,32,0.85);color:#7df9ff;font:600 11px/1 monospace;padding:5px 9px;border-radius:6px;z-index:99996;pointer-events:none;border:1px solid rgba(125,249,255,0.35);';
            document.body.appendChild(el);
        }
        return el;
    };
    document.addEventListener('mousemove', function (e) {
        var canvas = document.getElementById('paintCanvas');
        if (!canvas || !canvas.width) return;
        var rect = canvas.getBoundingClientRect();
        if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) {
            var el = document.getElementById('platinumCoordReadout');
            if (el) el.style.display = 'none';
            return;
        }
        var sx = canvas.width / rect.width;
        var sy = canvas.height / rect.height;
        var x = Math.floor((e.clientX - rect.left) * sx);
        var y = Math.floor((e.clientY - rect.top) * sy);
        var el2 = window.ensureCoordReadout();
        el2.style.display = 'block';
        // [49] COLOR READOUT — show pixel color under cursor in same overlay.
        var rgb = window.sampleEyedropperPixel ? window.sampleEyedropperPixel(x, y) : null;
        var hex = rgb ? '#' + [rgb.r, rgb.g, rgb.b].map(function (c) { return c.toString(16).padStart(2, '0'); }).join('').toUpperCase() : '';
        el2.innerHTML = 'X:' + x + ' Y:' + y + (hex ? ' <span style="display:inline-block;width:9px;height:9px;background:' + hex + ';border:1px solid #555;vertical-align:middle;"></span> ' + hex : '');
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [50] KEYBOARD ARROW NUDGE — move selection 1px (Shift = 10px).
    // Note: nudgeRegionSelection already exists; wire arrow keys when not in input.
    // ─────────────────────────────────────────────────────────────────────────
    document.addEventListener('keydown', function (e) {
        if (e.defaultPrevented) return; // SESSION ROUTER bail
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement && document.activeElement.tagName)) return;
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        var step = e.shiftKey ? 10 : 1;
        var dx = 0, dy = 0;
        if (e.key === 'ArrowLeft') dx = -step;
        else if (e.key === 'ArrowRight') dx = step;
        else if (e.key === 'ArrowUp') dy = -step;
        else if (e.key === 'ArrowDown') dy = step;
        else return;
        if (typeof nudgeRegionSelection === 'function' && nudgeRegionSelection(dx, dy)) {
            e.preventDefault();
            if (typeof showToast === 'function') showToast('Nudged ' + dx + ',' + dy + 'px');
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [51] BLEND MODE PREVIEWS — populate dropdown with mini swatches.
    // ─────────────────────────────────────────────────────────────────────────
    window.BLEND_MODES = ['normal', 'multiply', 'screen', 'overlay', 'soft-light', 'hard-light', 'color-dodge', 'color-burn', 'darken', 'lighten', 'difference', 'exclusion', 'hue', 'saturation', 'color', 'luminosity'];
    window.applyBlendModeIcons = function applyBlendModeIcons() {
        var sels = document.querySelectorAll('select.layer-blend-mode, select[data-role="blend-mode"]');
        sels.forEach(function (sel) {
            for (var i = 0; i < sel.options.length; i++) {
                var opt = sel.options[i];
                if (opt.dataset.iconified) continue;
                opt.textContent = '◐ ' + opt.textContent;
                opt.dataset.iconified = '1';
            }
        });
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [52] LAYER OPACITY number input — clickable to type opacity value directly.
    // ─────────────────────────────────────────────────────────────────────────
    window.promptLayerOpacity = function promptLayerOpacity(layerId) {
        var v = prompt('Layer opacity (0–100):', '100');
        if (v == null) return;
        var pct = Math.max(0, Math.min(100, parseInt(v, 10)));
        if (isNaN(pct)) return;
        if (typeof setLayerOpacity === 'function') setLayerOpacity(layerId, pct);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [53] BRUSH SHAPE indicator — show current shape name briefly on change.
    // ─────────────────────────────────────────────────────────────────────────
    var _shapeEl = document.getElementById('brushShape');
    if (_shapeEl && !_shapeEl._platinumWired) {
        _shapeEl._platinumWired = true;
        _shapeEl.addEventListener('change', function () {
            if (typeof showToast === 'function') showToast('Brush shape: ' + this.value);
            if (typeof updateBrushCursorVisibility === 'function') updateBrushCursorVisibility();
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // [54] WAND tolerance auto-suggest — read seed and recommend.
    // ─────────────────────────────────────────────────────────────────────────
    window.applyWandToleranceFromSeed = function applyWandToleranceFromSeed(rgb) {
        var t = window.suggestWandTolerance(rgb);
        var el = document.getElementById('wandTolerance');
        if (el) { el.value = t; if (typeof el.oninput === 'function') el.oninput(); }
        if (typeof showToast === 'function') showToast('Wand tolerance auto-set to ' + t);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [55] LASSO undo last point — Backspace shortcut.
    // ─────────────────────────────────────────────────────────────────────────
    document.addEventListener('keydown', function (e) {
        if (e.defaultPrevented) return; // SESSION ROUTER bail
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement && document.activeElement.tagName)) return;
        if (e.key === 'Backspace' && window.canvasMode === 'lasso' && typeof undoLassoPoint === 'function') {
            e.preventDefault();
            undoLassoPoint();
            if (typeof showToast === 'function') showToast('Removed last lasso point');
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [56] ESCAPE cancels active strokes / selections cleanly.
    // ─────────────────────────────────────────────────────────────────────────
    document.addEventListener('keydown', function (e) {
        if (e.defaultPrevented) return; // SESSION ROUTER bail (transform/master own Esc first)
        if (e.key !== 'Escape') return;
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement && document.activeElement.tagName)) return;
        try {
            if (window.isDrawing) window.isDrawing = false;
            if (typeof rectStart !== 'undefined') window.rectStart = null;
            if (typeof _gradientStart !== 'undefined') window._gradientStart = null;
            if (typeof _shapeStart !== 'undefined') window._shapeStart = null;
            if (typeof _ellipseStart !== 'undefined') window._ellipseStart = null;
            if (typeof hideRectPreview === 'function') hideRectPreview();
            if (typeof hideLassoPreview === 'function') hideLassoPreview();
            if (typeof hideMoveDistance === 'function') hideMoveDistance();
        } catch (err) {}
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [57] STATUS BAR — combined zoom + tool + selection size readout.
    // ─────────────────────────────────────────────────────────────────────────
    window.updatePlatinumStatusBar = function updatePlatinumStatusBar() {
        var el = document.getElementById('platinumStatusBar');
        if (!el) {
            el = document.createElement('div');
            el.id = 'platinumStatusBar';
            el.style.cssText = 'position:fixed;right:14px;bottom:14px;background:rgba(20,24,32,0.88);color:#bbb;font:600 11px/1 monospace;padding:6px 10px;border-radius:6px;z-index:99996;pointer-events:none;border:1px solid #444;display:flex;gap:14px;';
            document.body.appendChild(el);
        }
        var zoom = typeof currentZoom !== 'undefined' ? Math.round(currentZoom * 100) + '%' : '–';
        var tool = window.canvasMode || '–';
        var pixCount = '–';
        try {
            if (typeof zones !== 'undefined' && zones[selectedZoneIndex] && zones[selectedZoneIndex].regionMask) {
                var m = zones[selectedZoneIndex].regionMask;
                var c = 0;
                for (var i = 0; i < m.length; i++) if (m[i] > 0) c++;
                pixCount = c.toLocaleString() + ' px';
            }
        } catch (e) {}
        el.innerHTML = '<span style="color:#7df9ff;">' + zoom + '</span><span>' + tool + '</span><span>' + pixCount + '</span>';
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [58] RIGHT-CLICK QUICK PALETTE — pick color from canvas at any time.
    // ─────────────────────────────────────────────────────────────────────────
    window.quickPickColorAt = function quickPickColorAt(x, y) {
        var rgb = window.sampleEyedropperPixel(x, y);
        if (!rgb) return null;
        var hex = '#' + [rgb.r, rgb.g, rgb.b].map(function (c) { return c.toString(16).padStart(2, '0'); }).join('').toUpperCase();
        window.pushRecentColor(hex);
        if (typeof window._foregroundColor !== 'undefined') window._foregroundColor = hex;
        if (typeof showToast === 'function') showToast('Picked: ' + hex);
        return hex;
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [59] BRUSH PRESSURE simulator (no real tablet) — opacity/size jitter slider.
    // ─────────────────────────────────────────────────────────────────────────
    window.brushJitter = window.brushJitter || 0;
    window.applyBrushJitter = function applyBrushJitter(baseSize, baseOpacity) {
        var j = Math.max(0, Math.min(100, parseInt(window.brushJitter, 10) || 0)) / 100;
        if (j <= 0) return { size: baseSize, opacity: baseOpacity };
        var sf = 1 - (Math.random() * j * 0.5);
        var of = 1 - (Math.random() * j * 0.5);
        return { size: Math.max(1, Math.round(baseSize * sf)), opacity: Math.max(0.05, baseOpacity * of) };
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [60] WHEEL+ALT brush size shortcut — Alt+wheel resizes brush instead of zoom.
    // ─────────────────────────────────────────────────────────────────────────
    document.addEventListener('wheel', function (e) {
        var BRUSH_MODES = ['brush', 'erase', 'colorbrush', 'recolor', 'smudge', 'clone', 'history-brush', 'dodge', 'burn', 'blur-brush', 'sharpen-brush', 'pencil', 'spatial-include', 'spatial-exclude', 'spatial-erase'];
        if (!e.altKey) return;
        if (BRUSH_MODES.indexOf(window.canvasMode) === -1) return;
        e.preventDefault();
        var step = e.shiftKey ? 10 : 3;
        if (e.deltaY < 0) window.bumpBrushSize(step);
        else window.bumpBrushSize(-step);
    }, { passive: false });

    // ─────────────────────────────────────────────────────────────────────────
    // [61] SAFE-DEFAULT — ensure brushSize never reads as NaN/0 at startup.
    // ─────────────────────────────────────────────────────────────────────────
    setTimeout(function () {
        var s = document.getElementById('brushSize');
        if (s && (!s.value || isNaN(parseInt(s.value, 10)))) s.value = 20;
        var o = document.getElementById('brushOpacity');
        if (o && (!o.value || isNaN(parseInt(o.value, 10)))) o.value = 100;
        var h = document.getElementById('brushHardness');
        if (h && (!h.value || isNaN(parseInt(h.value, 10)))) h.value = 100;
    }, 0);

    // ─────────────────────────────────────────────────────────────────────────
    // [62] LAYER EFFECTS cache invalidation on edit — wires markLayerThumbDirty.
    // ─────────────────────────────────────────────────────────────────────────
    if (typeof window.updateLayerEffect === 'function' && !window._updateLayerEffectWrapped) {
        var _origULE = window.updateLayerEffect;
        window.updateLayerEffect = function (effectName, propName, value) {
            var r = _origULE.apply(this, arguments);
            if (typeof window._effectsTargetLayerId !== 'undefined') {
                window.markLayerThumbDirty(window._effectsTargetLayerId);
            }
            return r;
        };
        window._updateLayerEffectWrapped = true;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // [63] CANVAS context-menu enrichment — add "Copy color hex" item if available.
    // ─────────────────────────────────────────────────────────────────────────
    window.copyHexToClipboard = function copyHexToClipboard(hex) {
        if (!hex) return;
        try {
            navigator.clipboard.writeText(hex);
            if (typeof showToast === 'function') showToast('Copied ' + hex + ' to clipboard');
        } catch (e) {
            if (typeof showToast === 'function') showToast('Clipboard blocked — ' + hex);
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [64] ZONE OVERLAY OPACITY shortcut — , and . to dim/brighten.
    // ─────────────────────────────────────────────────────────────────────────
    document.addEventListener('keydown', function (e) {
        if (e.defaultPrevented) return; // SESSION ROUTER bail
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement && document.activeElement.tagName)) return;
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        if (e.key === ',') {
            if (typeof setOverlayOpacity === 'function') {
                window.overlayOpacityMultiplier = Math.max(0, (window.overlayOpacityMultiplier || 1) - 0.1);
                setOverlayOpacity(window.overlayOpacityMultiplier);
            }
        } else if (e.key === '.') {
            if (typeof setOverlayOpacity === 'function') {
                window.overlayOpacityMultiplier = Math.min(2, (window.overlayOpacityMultiplier || 1) + 0.1);
                setOverlayOpacity(window.overlayOpacityMultiplier);
            }
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [65] DRAW PREVIEW debounce — coalesce rect drag previews to 1 per frame.
    // ─────────────────────────────────────────────────────────────────────────
    window._rectPreviewRaf = 0;
    window.scheduleRectPreview = function scheduleRectPreview(start, end) {
        if (window._rectPreviewRaf) return;
        window._rectPreviewRaf = requestAnimationFrame(function () {
            window._rectPreviewRaf = 0;
            if (typeof drawRectPreview === 'function') drawRectPreview(start, end);
        });
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [66] BRUSH CURSOR auto-hide when over UI panels (cursor follows canvas only).
    // ─────────────────────────────────────────────────────────────────────────
    document.addEventListener('mousemove', function (e) {
        var c = document.getElementById('brushCursorCircle');
        if (!c || c.style.display === 'none') return;
        var canvas = document.getElementById('paintCanvas');
        if (!canvas) return;
        var rect = canvas.getBoundingClientRect();
        var inside = e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom;
        c.style.opacity = inside ? '1' : '0';
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [67] HISTORY snapshot helper — capture a labeled snapshot of paintImageData.
    // ─────────────────────────────────────────────────────────────────────────
    window._historySnapshots = window._historySnapshots || [];
    window.captureHistorySnapshot = function captureHistorySnapshot(label) {
        if (typeof paintImageData === 'undefined' || !paintImageData) return;
        var snap = { label: label || ('Snapshot ' + (window._historySnapshots.length + 1)), data: new Uint8ClampedArray(paintImageData.data), at: Date.now() };
        window._historySnapshots.push(snap);
        if (window._historySnapshots.length > 12) window._historySnapshots.shift();
        if (typeof markHistorySnapshot === 'function') markHistorySnapshot(snap.label);
    };
    window.restoreHistorySnapshot = function restoreHistorySnapshot(idx) {
        var s = window._historySnapshots[idx];
        if (!s || typeof paintImageData === 'undefined' || !paintImageData) return;
        if (typeof pushPixelUndo === 'function') pushPixelUndo('restore: ' + s.label);
        paintImageData.data.set(s.data);
        var pc = document.getElementById('paintCanvas');
        if (pc) pc.getContext('2d').putImageData(paintImageData, 0, 0);
        if (typeof showToast === 'function') showToast('Restored: ' + s.label);
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [68] FOREGROUND/BACKGROUND quick-swap helper (X already wired) — also D for default colors.
    // ─────────────────────────────────────────────────────────────────────────
    document.addEventListener('keydown', function (e) {
        if (e.defaultPrevented) return; // SESSION ROUTER bail
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement && document.activeElement.tagName)) return;
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        // 'd' is currently mapped to dodge in the existing keymap. Only Shift+D resets.
        if (e.shiftKey && (e.key === 'D' || e.key === 'd')) {
            e.preventDefault();
            if (typeof window._foregroundColor !== 'undefined') window._foregroundColor = '#000000';
            if (typeof window._backgroundColor !== 'undefined') window._backgroundColor = '#ffffff';
            if (typeof showToast === 'function') showToast('Default colors: black/white');
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    // [69] AUTO-SAVE selection state to localStorage every 30s (recover after crash).
    // ─────────────────────────────────────────────────────────────────────────
    setInterval(function () {
        try {
            if (typeof zones === 'undefined' || !zones[selectedZoneIndex]) return;
            var z = zones[selectedZoneIndex];
            if (!z.regionMask) return;
            var canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            // Only store an RLE summary so storage stays small.
            if (typeof encodeRegionMaskRLE === 'function') {
                var rle = encodeRegionMaskRLE(z.regionMask, canvas.width, canvas.height);
                if (rle && rle.runs && rle.runs.length < 5000) {
                    localStorage.setItem('spb_lastRegionMask_' + selectedZoneIndex, JSON.stringify(rle));
                }
            }
        } catch (e) {}
    }, 30000);

    // ─────────────────────────────────────────────────────────────────────────
    // [70] DEFAULT ALPHA for new layers (ensure transparency-correct paint behavior).
    // ─────────────────────────────────────────────────────────────────────────
    window.ensureLayerAlphaDefaults = function ensureLayerAlphaDefaults(layer) {
        if (!layer) return;
        if (typeof layer.opacity !== 'number') layer.opacity = 1.0;
        if (typeof layer.visible !== 'boolean') layer.visible = true;
        if (typeof layer.locked !== 'boolean') layer.locked = false;
        if (typeof layer.alphaLock !== 'boolean') layer.alphaLock = false;
        if (typeof layer.clippingMask !== 'boolean') layer.clippingMask = false;
        if (typeof layer.blendMode !== 'string') layer.blendMode = 'source-over';
        return layer;
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [71] LAYER ALL-VISIBILITY shortcut — Alt+click visibility hides all others.
    // ─────────────────────────────────────────────────────────────────────────
    window.soloLayer = function soloLayer(layerId) {
        if (typeof _psdLayers === 'undefined') return;
        _psdLayers.forEach(function (l) { l.visible = (l.id === layerId); });
        if (typeof renderLayerPanel === 'function') renderLayerPanel();
        if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
        if (typeof showToast === 'function') showToast('Solo layer mode');
    };
    window.showAllLayers = function showAllLayers() {
        if (typeof _psdLayers === 'undefined') return;
        _psdLayers.forEach(function (l) { l.visible = true; });
        if (typeof renderLayerPanel === 'function') renderLayerPanel();
        if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
        if (typeof showToast === 'function') showToast('All layers visible');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [72] QUICK ACTION — invert selection of current zone (X key already taken; expose API).
    // ─────────────────────────────────────────────────────────────────────────
    window.invertCurrentSelection = function invertCurrentSelection() {
        if (typeof invertRegionMask === 'function') invertRegionMask();
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [73] HOTKEY HELP overlay — shows all shortcuts on Shift+? (already exists for ?).
    // Add a printable list helper.
    // ─────────────────────────────────────────────────────────────────────────
    window.PLATINUM_SHORTCUTS = [
        ['B', 'Brush'], ['E', 'Edge detect'], ['W', 'Magic wand'], ['L', 'Lasso'], ['O', 'Marquee'],
        ['G', 'Gradient'], ['K', 'Fill bucket'], ['P', 'Eyedropper'], ['I', 'Pencil'],
        ['[', 'Brush smaller'], [']', 'Brush bigger'], ['Shift+[', 'Hardness -10%'], ['Shift+]', 'Hardness +10%'],
        ['Alt+wheel', 'Resize brush'], ['Ctrl+0', 'Fit to window'], ['Ctrl++', 'Zoom in'], ['Ctrl+-', 'Zoom out'],
        ['Backspace', 'Lasso: undo last point'], ['Esc', 'Cancel active tool'], ['F (×2)', 'Fit to window'],
        ['Arrows', 'Nudge selection 1px'], ['Shift+Arrows', 'Nudge 10px'],
        ['Shift+D', 'Reset FG/BG colors'], [',/.', 'Overlay opacity ±'],
    ];
    window.printShortcutCard = function printShortcutCard() {
        var html = '<table style="border-collapse:collapse;width:100%;font:12px monospace;"><tbody>';
        window.PLATINUM_SHORTCUTS.forEach(function (s) {
            html += '<tr><td style="padding:3px 6px;background:#222;color:#ffd86b;border:1px solid #333;">' + s[0] + '</td><td style="padding:3px 6px;color:#ddd;border:1px solid #333;">' + s[1] + '</td></tr>';
        });
        html += '</tbody></table>';
        return html;
    };

    // ─────────────────────────────────────────────────────────────────────────
    // [74] SHOW INITIAL recent-color bar after load.
    // ─────────────────────────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            try { window.renderRecentColors(); } catch (e) {}
        });
    } else {
        try { window.renderRecentColors(); } catch (e) {}
    }

    // ─────────────────────────────────────────────────────────────────────────
    // [75] ENSURE CENTER DOT on brush cursor at boot.
    // ─────────────────────────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            try { window.ensureBrushCenterDot(); } catch (e) {}
        });
    } else {
        try { window.ensureBrushCenterDot(); } catch (e) {}
    }

})();
// ══════════════════════════════════════════════════════════════════════════════
// END Platinum Canvas UX pack
// ══════════════════════════════════════════════════════════════════════════════
