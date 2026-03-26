// ============================================================
// PAINT-BOOTH-7-SHOKK.JS - SHOKK File System for Paint Booth V5
// ============================================================
// Manages .shokk paint recipe files:
//   - Save as SHOKK (bake spec + session + paint into one file)
//   - SHOKK Library browser (thumbnail grid of all saved files)
//   - Open SHOKK (load zone config + locked baked spec)
//   - Export spec channels for Photoshop (4 separate PNGs)
//   - Blank Canvas mode (start fresh without a car paint TGA)
// ============================================================

// ─── STATE ────────────────────────────────────────────────────────────────────

let _shokkLibraryData = [];
let _shokkLibraryPath = '';

// ─── OPEN SHOKK LIBRARY ───────────────────────────────────────────────────────
// PS_EXPORT_FOLDER_KEY is defined in paint-booth-5-api-render.js (script loads first). Do not redeclare.

/** Open a folder picker and set the PS Export folder input. Works in Electron (full path); in browser user may need to paste path. */
function browsePsExportFolder(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    // Electron: use dialog if available
    if (typeof window !== 'undefined' && window.electronAPI && typeof window.electronAPI.showFolderDialog === 'function') {
        window.electronAPI.showFolderDialog().then(function (path) {
            if (path) {
                input.value = path;
                var other = inputId === 'leftPanelPsExportFolder' ? document.getElementById('shokkPsExportFolder') : document.getElementById('leftPanelPsExportFolder');
                if (other) other.value = path;
                if (typeof localStorage !== 'undefined') localStorage.setItem(PS_EXPORT_FOLDER_KEY, path);
                if (typeof showToast === 'function') showToast('PS Export folder set: ' + path);
            }
        }).catch(function () {});
        return;
    }
    // Browser: use directory picker (may not expose full path)
    var el = document.createElement('input');
    el.type = 'file';
    el.style.display = 'none';
    el.setAttribute('webkitdirectory', '');
    el.setAttribute('directory', '');
    el.addEventListener('change', function () {
        var files = el.files;
        if (!files || files.length === 0) return;
        var first = files[0];
        var dirPath = '';
        if (first.path) {
            dirPath = first.path.replace(/[\\/][^\\/]*$/, '');
        } else if (first.webkitRelativePath) {
            var parts = first.webkitRelativePath.split(/[\\/]/);
            parts.pop();
            dirPath = parts.join('/');
        }
        if (dirPath) {
            input.value = dirPath;
            var other = inputId === 'leftPanelPsExportFolder' ? document.getElementById('shokkPsExportFolder') : document.getElementById('leftPanelPsExportFolder');
            if (other) other.value = dirPath;
            if (typeof localStorage !== 'undefined') localStorage.setItem(PS_EXPORT_FOLDER_KEY, dirPath);
            if (typeof showToast === 'function') showToast('PS Export folder set');
        } else {
            if (typeof showToast === 'function') showToast('Browsers don\'t expose folder path — type or paste the full path in the box, or run in Electron for Browse.', true);
        }
        document.body.removeChild(el);
    });
    document.body.appendChild(el);
    el.click();
}

function openShokkLibrary() {
    try {
        const modal = document.getElementById('shokkLibraryModal');
        if (!modal) { console.warn('[SHOKK] Library modal not found'); return; }
        modal.style.display = 'flex';
    var saved = typeof localStorage !== 'undefined' ? localStorage.getItem(PS_EXPORT_FOLDER_KEY) || '' : '';
    var folderEl = document.getElementById('shokkPsExportFolder');
    if (folderEl) folderEl.value = saved;
    var leftEl = document.getElementById('leftPanelPsExportFolder');
    if (leftEl) leftEl.value = saved;
    _loadShokkLibraryContents();
    } catch (e) {
        console.error('[SHOKK] openShokkLibrary error:', e);
        if (typeof showToast === 'function') showToast('Could not open SHOKK Library: ' + e.message, true);
    }
}

function closeShokkLibrary() {
    const modal = document.getElementById('shokkLibraryModal');
    if (modal) modal.style.display = 'none';
}

function _shokkApiBase() {
    if (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) return ShokkerAPI.baseUrl;
    // Fallback when page is served by server (e.g. same origin)
    if (typeof window !== 'undefined' && window.location && window.location.origin) return window.location.origin;
    return '';
}

function _setShokkSpecUiState(state, label) {
    const chip = document.getElementById('shokkSpecStateChip');
    const specBanner = document.getElementById('specFromShokkBanner');
    const specLabel = document.getElementById('specFromShokkLabel');
    if (chip) {
        if (state === 'loaded') {
            chip.textContent = 'SPEC: loaded';
            chip.style.color = 'var(--accent-green)';
            chip.style.borderColor = 'rgba(0,200,80,0.6)';
            chip.style.background = 'rgba(0,200,80,0.12)';
            chip.title = label || 'Spec map is loaded and will be used for render';
        } else if (state === 'missing') {
            chip.textContent = 'SPEC: missing';
            chip.style.color = '#ff6666';
            chip.style.borderColor = 'rgba(255,80,80,0.7)';
            chip.style.background = 'rgba(255,80,80,0.12)';
            chip.title = label || 'This SHOKK has no spec map payload';
        } else {
            chip.textContent = 'SPEC: none';
            chip.style.color = 'var(--text-dim)';
            chip.style.borderColor = 'var(--border)';
            chip.style.background = 'rgba(255,255,255,0.03)';
            chip.title = 'Current SHOKK spec status';
        }
    }
    if (specBanner) {
        if (state === 'loaded') {
            specBanner.style.display = 'block';
            specBanner.style.borderColor = 'rgba(0,200,80,0.5)';
            specBanner.style.background = 'linear-gradient(135deg, rgba(0,200,80,0.15), rgba(0,150,200,0.08))';
            if (specLabel) specLabel.textContent = label || 'Spec loaded — zones paint on top. Render uses this spec.';
        } else if (state === 'missing') {
            specBanner.style.display = 'block';
            specBanner.style.borderColor = 'rgba(255,80,80,0.7)';
            specBanner.style.background = 'linear-gradient(135deg, rgba(255,60,60,0.12), rgba(120,20,20,0.10))';
            if (specLabel) specLabel.textContent = label || 'No spec map found in this SHOKK file.';
        } else {
            specBanner.style.display = 'none';
            specBanner.style.borderColor = 'rgba(0,200,80,0.5)';
            specBanner.style.background = 'linear-gradient(135deg, rgba(0,200,80,0.15), rgba(0,150,200,0.08))';
        }
    }
}

async function _loadShokkLibraryContents() {
    const grid = document.getElementById('shokkLibraryGrid');
    const status = document.getElementById('shokkLibraryStatus');
    if (!grid) return;
    grid.innerHTML = '<div style="color:var(--text-dim);font-size:12px;padding:20px;">Loading SHOKK Library…</div>';

    const base = _shokkApiBase();
    try {
        // Use same API base as rest of app so library works when page origin differs (e.g. file:// or different port)
        const pathRes = await fetch(base + '/api/shokk/library-path');
        if (pathRes.ok) {
            const pathData = await pathRes.json();
            _shokkLibraryPath = pathData.path || '';
            const pathEl = document.getElementById('shokkLibraryPathLabel');
            if (pathEl) pathEl.textContent = _shokkLibraryPath;
        }

        const res = await fetch(base + '/api/shokk/list');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'List failed');

        _shokkLibraryData = data.shokks || [];
        _renderShokkGrid(_shokkLibraryData);

        if (status) status.textContent = `${_shokkLibraryData.length} file${_shokkLibraryData.length !== 1 ? 's' : ''}`;
    } catch (e) {
        grid.innerHTML = `<div style="color:#ff6666;padding:20px;font-size:12px;">Error loading library: ${e.message}</div>`;
    }
}

function _renderShokkGrid(entries, filter = '') {
    const grid = document.getElementById('shokkLibraryGrid');
    if (!grid) return;

    const lf = filter.toLowerCase();
    const filtered = lf
        ? entries.filter(e =>
            (e.name || '').toLowerCase().includes(lf) ||
            (e.author || '').toLowerCase().includes(lf) ||
            (e.tags || []).some(t => t.toLowerCase().includes(lf)) ||
            (e.description || '').toLowerCase().includes(lf)
        )
        : entries;

    if (!filtered.length) {
        grid.innerHTML = `<div style="color:var(--text-dim);font-size:12px;padding:32px;text-align:center;">
            ${lf ? `No SHOKK files match "${filter}"` : 'No SHOKK files yet.<br><br>Render something, then click <strong>🔥 Save SHOKK</strong> to create your first one!'}
        </div>`;
        return;
    }

    // Group by source: factory first
    const factory = filtered.filter(e => e.source === 'factory');
    const user = filtered.filter(e => e.source !== 'factory');

    let html = '';

    if (factory.length) {
        html += `<div class="shokk-section-label">FACTORY</div>`;
        html += factory.map(e => _shokkCard(e)).join('');
    }
    if (user.length) {
        html += `<div class="shokk-section-label">YOUR LIBRARY</div>`;
        html += user.map(e => _shokkCard(e)).join('');
    }

    grid.innerHTML = html;
}

let _selectedShokkPath = '';

function _shokkCard(e) {
    const tags = (e.tags || []).map(t => `<span class="shokk-tag">${t}</span>`).join('');
    const meta = [
        e.author ? `by ${e.author}` : '',
        e.size_mb ? `${e.size_mb}MB` : '',
        e.has_spec ? '✓ Spec' : '',
        e.has_paint ? '✓ Paint' : '',
    ].filter(Boolean).join(' · ');
    const safePath = (e.path || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    const safeFilename = (e.filename || '').replace(/'/g, "\\'");

    const previewUrl = e.preview_url && !e.preview_url.startsWith('http') ? (_shokkApiBase() + (e.preview_url.startsWith('/') ? '' : '/') + e.preview_url) : (e.preview_url || '');
    const previewEl = previewUrl
        ? `<img src="${previewUrl.replace(/"/g, '&quot;')}" alt="preview" class="shokk-card-preview" onerror="this.style.display='none'">`
        : `<div class="shokk-card-no-preview">🎨</div>`;

    const deleteBtn = e.source !== 'factory'
        ? `<button class="shokk-card-delete" onclick="deleteShokkFile('${safeFilename}',event)" title="Delete this SHOKK file">✕</button>`
        : '';

    return `
<div class="shokk-card" onclick="selectShokkCard('${safePath}', this)" ondblclick="showShokkImportOptions('${safePath}')">
    ${deleteBtn}
    <div class="shokk-card-thumb">${previewEl}</div>
    <div class="shokk-card-body">
        <div class="shokk-card-name">${e.source === 'factory' ? '⭐ ' : ''}${e.name || e.filename}</div>
        <div class="shokk-card-meta">${meta}</div>
        <div class="shokk-card-tags">${tags}</div>
        ${e.description ? `<div class="shokk-card-desc">${e.description.substring(0, 80)}${e.description.length > 80 ? '…' : ''}</div>` : ''}
    </div>
    <button class="shokk-card-open" onclick="showShokkImportOptions('${safePath}');event.stopPropagation()">OPEN</button>
</div>`;
}

function selectShokkCard(path, el) {
    _selectedShokkPath = path;
    // Highlight selected card
    document.querySelectorAll('#shokkLibraryGrid .shokk-card').forEach(c => c.classList.remove('selected'));
    if (el) el.classList.add('selected');
    // Enable action buttons
    const psBtn = document.getElementById('shokkPsExportBtn');
    if (psBtn) psBtn.disabled = false;
}

function filterShokkLibrary(val) {
    _renderShokkGrid(_shokkLibraryData, val);
}

// ─── LOAD A SHOKK FILE ────────────────────────────────────────────────────────

// Import mode options:
//   'full'           = Restore everything: spec + zones + paint (original behavior)
//   'spec_only'      = Import ONLY the spec map as background canvas (keeps current paint + zones)
//   'spec_and_zones' = Import spec + zones but keep current paint
async function loadShokkFile(shokkPath, mode = 'full') {
    const base = _shokkApiBase();
    try {
        showToast(mode === 'full' ? 'Opening SHOKK file…' : 'Importing spec from SHOKK…');
        const res = await fetch(base + '/api/shokk/open', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: shokkPath })
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Open failed');

        const { manifest, session_json, spec_path, paint_path } = data;

        // Close the library modal
        closeShokkLibrary();

        // Apply zone config (skip in 'spec_only' and 'spec_and_new_tga' - keep user's current zones)
        if (mode !== 'spec_only' && mode !== 'spec_and_new_tga') {
            if (session_json && session_json.zones && typeof applySessionConfig === 'function') {
                applySessionConfig(session_json);
            } else if (session_json && session_json.zones) {
                if (typeof zones !== 'undefined') {
                    zones.length = 0;
                    (session_json.zones || []).forEach(z => zones.push(z));
                    if (typeof renderZoneList === 'function') renderZoneList();
                }
            }
        }

        // Apply baked spec if present (lock so next render uses this spec as background canvas)
        if (spec_path) {
            // Set BOTH global and window so doRender and any scope definitely sees it
            if (typeof importedSpecMapPath !== 'undefined') importedSpecMapPath = spec_path;
            try { window.importedSpecMapPath = spec_path; } catch (e) {}
            await fetch(base + '/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ imported_spec_path: spec_path })
            });
            const displayName = manifest.name || 'SHOKK';
            const specStatus = document.getElementById('importSpecMapStatus');
            if (specStatus) {
                specStatus.innerHTML = `<span style="color:var(--accent-green);font-weight:700;">✓ Spec active · Layer 0</span> — ${escapeHtml(displayName)}`;
                specStatus.style.color = '';
            }
            const clearBtn = document.getElementById('btnClearSpecMap');
            if (clearBtn) clearBtn.disabled = false;
            const loadedLabel = displayName + ' — zones paint on top. Render uses this spec.';
            _setShokkSpecUiState('loaded', loadedLabel);
            console.log('[SHOKK] Spec loaded:', spec_path);
            if (typeof renderZones === 'function') {
                renderZones();
                setTimeout(function () { if (typeof renderZones === 'function') renderZones(); }, 0);
            }
        } else {
            // Make missing spec impossible to miss
            if (typeof importedSpecMapPath !== 'undefined') importedSpecMapPath = null;
            try { window.importedSpecMapPath = null; } catch (e) {}
            const specStatus = document.getElementById('importSpecMapStatus');
            if (specStatus) {
                specStatus.innerHTML = `<span style="color:#ff6666;font-weight:700;">No spec map in this SHOKK</span>`;
                specStatus.style.color = '';
            }
            const clearBtn = document.getElementById('btnClearSpecMap');
            if (clearBtn) clearBtn.disabled = true;
            _setShokkSpecUiState('missing', 'This SHOKK file does not contain a baked spec map.');
            if (typeof showToast === 'function') showToast('This SHOKK has NO spec map payload.', true);
        }

        // Load paint file ONLY in 'full' mode (skip in spec_only and spec_and_zones)
        let didLoadPaint = false;
        if (mode === 'full') {
            let paintUrl = data.paint_url || (paint_path && (paint_path.startsWith('/') || paint_path.startsWith('http')) ? paint_path : null);
            // Ensure fetchable URL: relative paths need API base (e.g. Electron or different port)
            if (paintUrl && paintUrl.startsWith('/') && typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) {
                paintUrl = ShokkerAPI.baseUrl.replace(/\/$/, '') + paintUrl;
            }
            if (paintUrl && typeof loadPaintImageFromPath === 'function') {
                try {
                    await loadPaintImageFromPath(paintUrl);
                    didLoadPaint = true;
                } catch (paintErr) {
                    console.warn('[SHOKK] Baked paint load failed, will try local path fallback:', paintErr.message);
                }
            }

            // FALLBACK: If no paint was baked into the SHOKK (old saves before _latest_render fix),
            // try loading from the session's original paintFile path if it exists on disk
            if (!didLoadPaint && session_json && session_json.paintFile) {
                const localPaintPath = session_json.paintFile;
                const paintFileEl = document.getElementById('paintFile');
                if (paintFileEl) paintFileEl.value = localPaintPath;

                // Ask server to verify the file exists and serve it
                try {
                    const checkRes = await fetch(base + '/api/serve-local-file', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: localPaintPath })
                    });
                    if (checkRes.ok) {
                        const checkData = await checkRes.json();
                        if (checkData.ok && checkData.url && typeof loadPaintImageFromPath === 'function') {
                            let serveUrl = checkData.url;
                            if (serveUrl.startsWith('/') && typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) {
                                serveUrl = ShokkerAPI.baseUrl.replace(/\/$/, '') + serveUrl;
                            }
                            await loadPaintImageFromPath(serveUrl);
                            didLoadPaint = true;
                            console.log('[SHOKK] Paint loaded from local fallback path:', localPaintPath);
                        }
                    }
                } catch (fallbackErr) {
                    console.warn('[SHOKK] Local paint fallback failed:', fallbackErr.message);
                }

                // If server fallback didn't work, try Electron file:// protocol
                if (!didLoadPaint && localPaintPath && typeof loadPaintImageFromPath === 'function') {
                    // On Electron, file paths can be loaded directly
                    const filePath = localPaintPath.replace(/\\/g, '/');
                    const fileUrl = filePath.startsWith('/') ? 'file://' + filePath : 'file:///' + filePath;
                    try {
                        await loadPaintImageFromPath(fileUrl);
                        didLoadPaint = true;
                    } catch (fileErr) {
                        console.warn('[SHOKK] file:// paint load also failed:', fileErr.message);
                    }
                }

                if (!didLoadPaint) {
                    showToast('Paint file not baked in SHOKK. Set Source Paint path and load manually.', true);
                }
            }
        }

        const parts = [];
        if (spec_path) parts.push('spec locked');
        if (didLoadPaint) parts.push('paint loaded');
        else if (mode === 'full' && session_json && session_json.paintFile) parts.push('paint path set (load manually)');
        if (mode !== 'spec_only' && mode !== 'spec_and_new_tga') parts.push('zones restored');
        if (mode === 'spec_only' || mode === 'spec_and_new_tga') parts.push('zones kept');
        if (mode === 'spec_and_new_tga') {
            if (typeof showToast === 'function') showToast('Spec loaded. Choose your paint TGA (e.g. from Photoshop)…');
            _triggerTgaFilePickerForShokk();
        } else {
            if (typeof showToast === 'function') showToast(`✅ ${mode === 'full' ? 'Opened' : 'Imported'}: ${manifest.name || 'SHOKK'} [${parts.join(' · ')}]`);
        }

        // When spec was applied and we didn't load a paint image, update main area so user sees "Spec from SHOKK loaded"
        if (spec_path && !didLoadPaint) {
            _showSpecLoadedFromShokkState(manifest.name || 'SHOKK');
        }

    } catch (e) {
        console.error('[SHOKK] Open error:', e);
        if (typeof showToast === 'function') showToast(`❌ SHOKK open failed: ${e.message}`, true);
    }
}

/** Update the main canvas area to show "Spec from SHOKK loaded" when we have spec but no paint image yet. */
function _showSpecLoadedFromShokkState(shokkName) {
    const emptyBig = document.getElementById('paintPreviewEmptyBig');
    if (!emptyBig) return;
    emptyBig.innerHTML = `
        <div class="onboarding-icon" style="color:var(--accent-green);">✓</div>
        <h2 style="color: var(--accent-green); font-size: 18px; font-weight: 700; margin-bottom: 12px;">Spec map from SHOKK loaded</h2>
        <p style="color: var(--text-dim); font-size: 13px; margin-bottom: 16px;">${escapeHtml(shokkName || 'SHOKK')} — spec is active as Layer 0. You can render with this spec, or load a paint TGA to pair with it.</p>
        <button class="btn btn-accent" onclick="openPaintFilePicker()"
            style="margin-top: 8px; padding: 10px 24px; font-size: 14px; border-radius: 8px;">
            Load Paint Image
        </button>
        <p style="color: var(--text-dim); font-size: 11px; margin-top: 12px;">Or assign finishes to zones and hit <strong style="color:var(--success);">RENDER</strong>.</p>
    `;
}

// ─── IMPORT OPTIONS DIALOG ────────────────────────────────────────────────────
// Shows a quick chooser when user clicks OPEN on a SHOKK file

let _pendingShokkImportPath = '';  // Stored here so onclick doesn't need escaped paths

function _triggerTgaFilePickerForShokk() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.tga,.png,.jpg';
    input.style.display = 'none';
    input.onchange = async function () {
        const file = input.files && input.files[0];
        if (!file) { document.body.removeChild(input); return; }
        if (typeof window.loadPaintImageFromFile === 'function') {
            window.loadPaintImageFromFile(file);
        }
        // Set Source Paint so RENDER uses this file, not the old header path
        const paintFileEl = document.getElementById('paintFile');
        if (paintFileEl) {
            if (file.path) {
                paintFileEl.value = file.path;
                if (typeof showToast === 'function') showToast('Paint loaded. Source Paint set to selected file — render will use it.');
            } else {
                try {
                    const base = _shokkApiBase();
                    const form = new FormData();
                    form.append('file', file);
                    const res = await fetch(base + '/api/upload-paint-file', { method: 'POST', body: form });
                    const data = await res.json();
                    if (data.ok && data.path) {
                        paintFileEl.value = data.path;
                        if (typeof showToast === 'function') showToast('Paint loaded. Source Paint set — render will use your selected file.');
                    } else {
                        if (typeof showToast === 'function') showToast('Paint shown in preview but path not set — paste Source Paint path in header for render.', true);
                    }
                } catch (e) {
                    if (typeof showToast === 'function') showToast('Paint shown in preview. Set Source Paint path in header for render.', true);
                }
            }
        }
        document.body.removeChild(input);
    };
    document.body.appendChild(input);
    input.click();
}

function _doShokkImport(mode) {
    const modal = document.getElementById('shokkImportOptionsModal');
    if (modal) modal.style.display = 'none';
    if (_pendingShokkImportPath) {
        loadShokkFile(_pendingShokkImportPath, mode);
    }
}

function showShokkImportOptions(shokkPath) {
    _pendingShokkImportPath = shokkPath;

    // Always show the options modal so user can choose: Spec Only, Spec+New TGA, Spec+Zones, or Full.
    // (Previously we skipped the modal when no paint was loaded and went straight to 'full' — that hid the options.)

    // Build overlay dialog - z-index ABOVE the library (12000)
    let modal = document.getElementById('shokkImportOptionsModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'shokkImportOptionsModal';
        modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:13000;display:flex;align-items:center;justify-content:center;';
        modal.onclick = (e) => { if (e.target === modal) modal.style.display = 'none'; };
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
    <div style="background:var(--bg-panel,#12121f);border:1px solid var(--border,#333);border-radius:10px;padding:24px 28px;max-width:420px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.5);">
        <div style="font-size:15px;font-weight:700;color:var(--accent-gold,#ffaa00);margin-bottom:14px;">🔥 How do you want to open this SHOKK?</div>

        <button onclick="_doShokkImport('spec_only')"
            style="width:100%;padding:12px 14px;margin-bottom:8px;background:rgba(0,200,100,0.1);border:1px solid var(--accent-green,#00cc66);border-radius:6px;color:var(--accent-green,#00cc66);font-size:13px;font-weight:600;cursor:pointer;text-align:left;">
            🎯 Spec Map Only
            <div style="font-size:10px;color:var(--text-dim,#888);font-weight:400;margin-top:4px;">
                Import the spec map as background canvas (Zone 0). Keeps your current paint &amp; zones.
            </div>
        </button>

        <button onclick="_doShokkImport('spec_and_new_tga')"
            style="width:100%;padding:12px 14px;margin-bottom:8px;background:rgba(255,170,0,0.1);border:1px solid var(--accent-gold,#ffaa00);border-radius:6px;color:var(--accent-gold,#ffaa00);font-size:13px;font-weight:600;cursor:pointer;text-align:left;">
            🎨 Spec Map + New TGA
            <div style="font-size:10px;color:var(--text-dim,#888);font-weight:400;margin-top:4px;">
                Load spec from this SHOKK, then pick a paint TGA (e.g. your edited file from Photoshop) to pair with it.
            </div>
        </button>

        <button onclick="_doShokkImport('spec_and_zones')"
            style="width:100%;padding:12px 14px;margin-bottom:8px;background:rgba(100,150,255,0.1);border:1px solid var(--accent-blue,#3366ff);border-radius:6px;color:var(--accent-blue,#3366ff);font-size:13px;font-weight:600;cursor:pointer;text-align:left;">
            📋 Spec + Zones (Keep Paint)
            <div style="font-size:10px;color:var(--text-dim,#888);font-weight:400;margin-top:4px;">
                Import spec map and restore saved zone config, but keep your current paint loaded.
            </div>
        </button>

        <button onclick="_doShokkImport('full')"
            style="width:100%;padding:12px 14px;margin-bottom:8px;background:rgba(255,136,68,0.1);border:1px solid #ff8844;border-radius:6px;color:#ff8844;font-size:13px;font-weight:600;cursor:pointer;text-align:left;">
            📦 Full Import (Everything)
            <div style="font-size:10px;color:var(--text-dim,#888);font-weight:400;margin-top:4px;">
                Replace everything: load spec + zones + paint from the SHOKK file.
            </div>
        </button>

        <button onclick="document.getElementById('shokkImportOptionsModal').style.display='none'"
            style="width:100%;padding:8px;margin-top:4px;background:transparent;border:1px solid var(--border,#333);border-radius:6px;color:var(--text-dim,#888);font-size:12px;cursor:pointer;">
            Cancel
        </button>
    </div>`;
    modal.style.display = 'flex';
}

// ─── SAVE AS SHOKK ────────────────────────────────────────────────────────────

function openSaveShokkDialog() {
    try {
        const modal = document.getElementById('saveShokkModal');
        if (!modal) { console.warn('[SHOKK] Save modal not found'); return; }

        // Pre-populate author from config if available
        // NOTE: getConfig() reads from DOM. loadConfig() opens a file picker - DO NOT use that here.
        const cfg = (typeof getConfig === 'function' ? getConfig() : {}) || {};
        const authorField = document.getElementById('shokkSaveAuthor');
        if (authorField && !authorField.value) {
            authorField.value = cfg.author_name || '';
        }

        modal.style.display = 'flex';
    } catch (e) {
        console.error('[SHOKK] openSaveShokkDialog error:', e);
        if (typeof showToast === 'function') showToast('Could not open Save SHOKK: ' + e.message, true);
    }
}

function closeSaveShokkModal() {
    const modal = document.getElementById('saveShokkModal');
    if (modal) modal.style.display = 'none';
}

async function confirmSaveShokk() {
    try {
        const name = document.getElementById('shokkSaveName').value.trim();
        if (!name) { alert('Please enter a name for your SHOKK file.'); return; }

        const author = (document.getElementById('shokkSaveAuthor').value || '').trim();
        const description = (document.getElementById('shokkSaveDesc').value || '').trim();
        const includePaint = document.getElementById('shokkIncludePaint').checked;

        // Collect tags
        const tagCheckboxes = document.querySelectorAll('#saveShokkModal .shokk-tag-checkbox:checked');
        const tags = Array.from(tagCheckboxes).map(cb => cb.value);

        // Build session_json - serialize current zone config
        let session_json = {};
        if (typeof getSessionConfig === 'function') {
            session_json = getSessionConfig();
        } else if (typeof zones !== 'undefined') {
            session_json = { zones: JSON.parse(JSON.stringify(zones)) };
        }

        closeSaveShokkModal();
        if (typeof showToast === 'function') showToast('Saving SHOKK…');

        // Include the lastRenderedJobId so the server grabs the correct render
        const savePayload = { name, author, description, tags, session_json, include_paint: includePaint };
        if (typeof lastRenderedJobId !== 'undefined' && lastRenderedJobId) {
            savePayload.job_id = lastRenderedJobId;
        }

        const base = _shokkApiBase();
        const res = await fetch(base + '/api/shokk/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(savePayload)
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Save failed');

        const parts = [data.has_spec ? '✓ Spec' : 'No spec (render first)', data.has_paint ? '✓ Paint' : ''].filter(Boolean);
        const savedDir = (data.path || '').replace(/[\\/][^\\/]*$/, '');
        if (typeof showToast === 'function') showToast(`✅ Saved: ${name}.shokk  [${parts.join(' · ')}]${savedDir ? '  →  ' + savedDir : ''}`);

    } catch (e) {
        console.error('[SHOKK] Save error:', e);
        if (typeof showToast === 'function') showToast(`❌ Save SHOKK failed: ${e.message}`, true);
    }
}

// ─── DELETE SHOKK ─────────────────────────────────────────────────────────────

async function deleteShokkFile(filename, event) {
    event.stopPropagation();
    if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    const base = _shokkApiBase();
    try {
        const res = await fetch(base + '/api/shokk/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json();
        if (data.ok) {
            showToast('SHOKK file deleted.');
            _loadShokkLibraryContents();
        } else {
            showToast(`Failed: ${data.error}`, true);
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, true);
    }
}

// ─── OPEN LIBRARY FOLDER ──────────────────────────────────────────────────────

async function openShokkLibraryFolder() {
    if (!_shokkLibraryPath) {
        const res = await fetch(_shokkApiBase() + '/api/shokk/library-path');
        if (res.ok) {
            const d = await res.json();
            _shokkLibraryPath = d.path || '';
        }
    }
    if (_shokkLibraryPath) {
        // Use Electron shell if available, otherwise copy to clipboard
        if (window.electronAPI && window.electronAPI.openPath) {
            window.electronAPI.openPath(_shokkLibraryPath);
        } else {
            navigator.clipboard.writeText(_shokkLibraryPath).then(() =>
                showToast(`✅ Path copied: ${_shokkLibraryPath}`));
        }
    }
}

// ─── EXPORT SPEC CHANNELS (PHOTOSHOP) ────────────────────────────────────────

async function exportSpecChannels(fromLibrary) {
    try {
        const body = {};
        var out = (document.getElementById('shokkPsExportFolder') && document.getElementById('shokkPsExportFolder').value.trim()) ||
            (document.getElementById('leftPanelPsExportFolder') && document.getElementById('leftPanelPsExportFolder').value.trim()) ||
            (typeof localStorage !== 'undefined' && localStorage.getItem(PS_EXPORT_FOLDER_KEY)) || '';
        var outputDir = out;
        if (outputDir) body.output_dir = outputDir;
        console.log('[PS Export] output_dir from inputs:', JSON.stringify(outputDir), '| body:', JSON.stringify(body));

        if (fromLibrary && _selectedShokkPath) {
            showToast('Extracting and exporting from SHOKK file…');
            body.shokk_path = _selectedShokkPath;
        } else {
            showToast('Exporting spec channels + paint for Photoshop…');
        }
        body.include_paint = true;

        const base = _shokkApiBase();
        const res = await fetch(base + '/api/export-spec-channels', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Export failed');

        const actualDir = data.out_dir || '';
        const paths = Object.values(data.paths);
        const fileCount = paths.length;
        console.log('[PS Export] Server used out_dir:', actualDir, '| files:', fileCount, '| paths:', JSON.stringify(data.paths));
        if (actualDir && typeof localStorage !== 'undefined') localStorage.setItem(PS_EXPORT_FOLDER_KEY, actualDir);
        showToast(`✅ ${fileCount} files exported to: ${actualDir}`);

        // Show a details panel
        const details = Object.entries(data.paths)
            .map(([ch, p]) => `${ch}: ${p.split(/[\\/]/).pop()}`)
            .join('\n');
        console.log('[SHOKK] Spec channels exported:\n' + details);

    } catch (e) {
        console.error('[SHOKK] Export spec channels error:', e);
        showToast(`❌ Export failed: ${e.message}`, true);
    }
}

// ─── BLANK CANVAS MODE ────────────────────────────────────────────────────────

async function loadBlankCanvas(width = 2048, height = 2048, color = 'ffffff') {
    try {
        showToast('Creating blank canvas…', 1500);
        // Download the blank TGA and trigger load as if user picked a file
        const base = _shokkApiBase();
        const url = base + `/api/blank-canvas?width=${width}&height=${height}&color=${color}`;

        // For Electron/local env: fetch the file and use as a blob
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to generate blank canvas');
        const blob = await res.blob();

        // Create a fake File object the existing loadPaintImage() can consume
        const file = new File([blob], 'blank_canvas.tga', { type: 'image/tga' });

        // Use existing paint image loader
        if (typeof loadPaintImageFromFile === 'function') {
            loadPaintImageFromFile(file);
        } else {
            // Fallback: create a data URL and load it directly
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    if (typeof _onPaintImageLoaded === 'function') _onPaintImageLoaded(img, 'blank_canvas.tga');
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        }

        showToast('✅ Blank canvas loaded - build your effects, then Save SHOKK!');
    } catch (e) {
        console.error('[SHOKK] Blank canvas error:', e);
        showToast(`❌ Blank canvas failed: ${e.message}`, true);
    }
}

// Pre-fill PS Export folder from localStorage when DOM is ready
(function () {
    function fill() {
        if (typeof localStorage === 'undefined') return;
        var v = localStorage.getItem(PS_EXPORT_FOLDER_KEY);
        if (!v) return;
        var el = document.getElementById('leftPanelPsExportFolder');
        if (el) el.value = v;
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fill);
    else fill();
})();
