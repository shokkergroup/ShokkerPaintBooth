// SHOKK DROP gallery helpers (pack drop + modal).
(function () {
    'use strict';

    var DROP_PACK_EXT = '.spbdrop';
    var LEGACY_DROP_PACK_EXT = '.spbshokk';
    var COMMUNITY_DROPS_URL = 'https://shokker-paint-booth.downndirtytn.chatgpt.site/drops';

    function _isDropPack(name) {
        var n = (name || '').toLowerCase();
        return n.endsWith(DROP_PACK_EXT) || n.endsWith(LEGACY_DROP_PACK_EXT);
    }

    function _esc(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    }

    function importUserImportPack(file) {
        var fd = new FormData();
        fd.append('pack', file);
        return fetch('/api/user-imports/import-pack', { method: 'POST', body: fd })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok) throw new Error((res.body && res.body.error) || 'Pack import failed');
                return res.body;
            });
    }

    function openCommunityDropsSite() {
        if (window.electronAPI && typeof window.electronAPI.openExternal === 'function') {
            window.electronAPI.openExternal(COMMUNITY_DROPS_URL);
            return;
        }
        window.open(COMMUNITY_DROPS_URL, '_blank', 'noopener,noreferrer');
    }

    function _communityModal() {
        var modal = document.getElementById('communityDropInstallModal');
        if (modal) return modal;
        modal = document.createElement('div');
        modal.id = 'communityDropInstallModal';
        modal.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,.88);z-index:10080;overflow:auto;padding:24px;';
        modal.addEventListener('click', function (ev) {
            if (ev.target === modal) modal.style.display = 'none';
        });
        document.body.appendChild(modal);
        return modal;
    }

    function _communityWebsite(value) {
        try {
            var url = new URL(value || '');
            return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : '';
        } catch (_) { return ''; }
    }

    function openCommunityDropInstall(id, version) {
        var toast = (typeof showToast === 'function') ? showToast : function (m) { console.log(m); };
        if (!/^drp_[a-z0-9]{20,64}$/.test(String(id || '')) || Number(version || 1) !== 1) {
            toast('That SHOKK DROP link is invalid', 'error');
            return Promise.reject(new Error('Invalid SHOKK DROP link'));
        }
        toast('Verifying SHOKK DROP…', 'info');
        return fetch('/api/user-imports/community-drop/' + encodeURIComponent(id))
            .then(function (r) { return r.json().then(function (body) { return { ok: r.ok, body: body }; }); })
            .then(function (result) {
                if (!result.ok) throw new Error(result.body.error || 'Verification failed');
                var drop = result.body;
                var modal = _communityModal();
                var website = _communityWebsite(drop.author_website);
                modal.innerHTML =
                    '<div style="max-width:760px;margin:24px auto;background:var(--bg-panel,#171b23);border:1px solid var(--accent-cyan,#31d6ff);border-radius:12px;box-shadow:0 18px 80px #000;padding:18px;">' +
                    '<div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:12px;">' +
                    '<div style="flex:1;"><div style="font-size:9px;letter-spacing:.18em;color:var(--accent-cyan,#31d6ff);font-weight:800;">VERIFIED COMMUNITY SHOKK DROP</div>' +
                    '<h2 style="margin:5px 0 2px;font-size:21px;">' + _esc(drop.finish_name) + '</h2>' +
                    '<div style="font-size:11px;color:var(--text-dim,#9aa4b2);">by ' + _esc(drop.author_name) + '</div></div>' +
                    '<button type="button" id="communityDropClose" class="btn btn-sm">Close</button></div>' +
                    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">' +
                    '<figure style="margin:0;"><img src="' + _esc(drop.previews.paint) + '" alt="Base paint preview" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:7px;background:#090b0f;"><figcaption style="font-size:9px;margin-top:4px;color:var(--text-dim,#9aa4b2);">BASE PAINT</figcaption></figure>' +
                    '<figure style="margin:0;"><img src="' + _esc(drop.previews.spec) + '" alt="Spec preview" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:7px;background:#090b0f;"><figcaption style="font-size:9px;margin-top:4px;color:var(--text-dim,#9aa4b2);">SPEC MAP</figcaption></figure></div>' +
                    (drop.description ? '<p style="font-size:11px;line-height:1.5;color:var(--text-dim,#bac3ce);">' + _esc(drop.description) + '</p>' : '') +
                    (website ? '<button type="button" id="communityDropAuthorSite" class="btn btn-sm" style="margin-right:8px;">Author website</button>' : '') +
                    '<div style="margin-top:12px;padding:9px;border-radius:6px;background:#0c1118;font:9px monospace;color:#8da1b5;overflow-wrap:anywhere;">SHA-256 ' + _esc(drop.package.sha256) + '</div>' +
                    '<div style="display:flex;justify-content:flex-end;gap:8px;margin-top:14px;"><button type="button" id="communityDropInstall" class="btn btn-primary">Add to SHOKK DROP</button></div>' +
                    '</div>';
                modal.style.display = 'block';
                modal.querySelector('#communityDropClose').addEventListener('click', function () { modal.style.display = 'none'; });
                var authorButton = modal.querySelector('#communityDropAuthorSite');
                if (authorButton) authorButton.addEventListener('click', function () {
                    if (window.electronAPI && window.electronAPI.openExternal) window.electronAPI.openExternal(website);
                    else window.open(website, '_blank', 'noopener,noreferrer');
                });
                modal.querySelector('#communityDropInstall').addEventListener('click', function () {
                    var button = this;
                    button.disabled = true;
                    button.textContent = 'Downloading + verifying…';
                    fetch('/api/user-imports/install-community-drop', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: drop.id, version: drop.version })
                    })
                        .then(function (r) { return r.json().then(function (body) { return { ok: r.ok, body: body }; }); })
                        .then(function (installed) {
                            if (!installed.ok) throw new Error(installed.body.error || 'Install failed');
                            var entry = installed.body.imported && installed.body.imported[0];
                            modal.style.display = 'none';
                            toast('Added “' + ((entry && entry.name) || drop.finish_name) + '” to SHOKK DROP', 'success');
                            window._userImportsGalleryCache = null;
                            openUserImportGalleryFromApi();
                        })
                        .catch(function (err) {
                            button.disabled = false;
                            button.textContent = 'Try again';
                            toast('SHOKK DROP install failed: ' + err.message, 'error');
                        });
                });
                return drop;
            })
            .catch(function (err) {
                toast('SHOKK DROP verification failed: ' + err.message, 'error');
                throw err;
            });
    }

    function handleCommunityDeepLink(rawUrl) {
        try {
            var parsed = new URL(rawUrl);
            if (parsed.protocol !== 'shokker:' || parsed.hostname !== 'drop' || parsed.pathname !== '/install') return;
            openCommunityDropInstall(parsed.searchParams.get('id'), Number(parsed.searchParams.get('version') || 1));
        } catch (_) {
            var toast = (typeof showToast === 'function') ? showToast : function () {};
            toast('That SHOKK DROP link is invalid', 'error');
        }
    }

    function bindPackDropZone(el, onDone) {
        if (!el || el.dataset.uiDropBound) return;
        el.dataset.uiDropBound = '1';
        el.addEventListener('dragover', function (e) {
            e.preventDefault();
            el.style.outline = '2px dashed var(--accent-cyan,#7dd3fc)';
        });
        el.addEventListener('dragleave', function () {
            el.style.outline = '';
        });
        el.addEventListener('drop', function (e) {
            e.preventDefault();
            el.style.outline = '';
            var files = [];
            var dropped = 0;
            if (e.dataTransfer && e.dataTransfer.files) {
                dropped = e.dataTransfer.files.length;
                for (var i = 0; i < e.dataTransfer.files.length; i++) {
                    var f = e.dataTransfer.files[i];
                    if (_isDropPack(f.name)) files.push(f);
                }
            }
            var toast = (typeof showToast === 'function') ? showToast : function () {};
            if (!files.length) {
                // Something WAS dropped but nothing was a pack — say so instead
                // of silently doing nothing (usually an image aimed at the
                // wrong zone: art imports go through the sidebar).
                if (dropped) {
                    toast('This zone takes ' + DROP_PACK_EXT + ' packs — drop art (PNG/JPG/WebP) on the left sidebar instead', 'info');
                }
                return;
            }
            toast('Importing ' + files.length + ' pack(s)…', 'info');
            Promise.all(files.map(importUserImportPack))
                .then(function (results) {
                    var imported = [];
                    (results || []).forEach(function (r) {
                        (r && r.imported || []).forEach(function (e) { imported.push(e); });
                    });
                    var names = imported.map(function (e) { return e.name || e.id; });
                    var msg = !imported.length
                        ? 'Pack(s) imported'
                        : imported.length === 1
                            ? 'Imported “' + names[0] + '”'
                            : 'Imported ' + imported.length + ' drop(s): ' +
                              names.slice(0, 3).join(', ') + (names.length > 3 ? '…' : '');
                    toast(msg, 'success');
                    if (typeof onDone === 'function') onDone(imported);
                })
                .catch(function (err) { toast('Import failed: ' + err.message, 'error'); });
        });
    }

    function _gauntletBadgeHtml(e) {
        var isPaint = !e.kind || e.kind === 'paint_monolithic';
        if (!isPaint) return '';
        var dna = e.import_dna;
        if (!dna || !dna.gauntlet_stats) return '';
        var st = dna.gauntlet_stats;
        var passed = !!dna.gauntlet_passed;
        var label = passed ? 'PASS' : 'FAIL';
        var short = 'M' + Math.round(st.M_std || 0) + ' R' + Math.round(st.R_std || 0) + ' C' + Math.round(st.C_std || 0);
        var tip = 'Import DNA gauntlet: ' + label +
            ' | M σ=' + (st.M_std || 0) + ' R σ=' + (st.R_std || 0) + ' C σ=' + (st.C_std || 0);
        var color = passed ? '#8fd8a0' : '#f0a8a8';
        var border = passed ? '#2a6b3a' : '#6b2a2a';
        return '<span title="' + _esc(tip) + '" style="display:inline-block;font-size:7px;font-weight:700;padding:1px 4px;border-radius:3px;margin-top:3px;color:' + color + ';border:1px solid ' + border + ';">' +
            _esc(label + ' · ' + short) + '</span>';
    }

    function copyUserImportShareLink(id, btn) {
        if (!id) return;
        var url = window.location.origin + '/api/user-imports/export/' + encodeURIComponent(id);
        var toast = (typeof showToast === 'function') ? showToast : function (m) { console.log(m); };
        var done = function () {
            toast('Share link copied', 'success');
            if (btn) {
                var prev = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(function () { btn.textContent = prev; }, 1600);
            }
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(done).catch(function () { toast(url, 'info'); });
            return;
        }
        var ta = document.createElement('textarea');
        ta.value = url;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); done(); } catch (e) { toast(url, 'info'); }
        ta.remove();
    }

    function renderGalleryGrid(entries) {
        if (!entries.length) {
            return '<div style="padding:1rem;color:var(--text-dim);font-size:11px;">No imports yet.</div>';
        }
        return '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;padding:8px;">' +
            entries.map(function (e) {
                var dna = e.import_dna ? e.import_dna.style : '';
                var author = e.author || e.author_name || '';
                var isPaint = !e.kind || e.kind === 'paint_monolithic';
                var thumb = '<img src="/api/user-imports/preview-image/' + e.id + '?t=' + Date.now() + '" alt="" style="width:100%;border-radius:4px;background:#111;">';
                return '<article style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:6px;padding:6px;">' +
                    thumb +
                    '<div style="font-size:9px;margin-top:4px;font-weight:600;overflow:hidden;text-overflow:ellipsis;" title="' + _esc(e.id) + '">' +
                    _esc(e.name || e.id) + '</div>' +
                    '<div style="font-size:8px;color:var(--text-dim);">' + _esc(e.kind || 'paint') +
                    (dna ? ' · ' + _esc(dna) : '') + '</div>' +
                    (author ? '<div style="font-size:8px;color:var(--accent-cyan,#7dd3fc);margin-top:2px;">by ' + _esc(author) + '</div>' : '') +
                    _gauntletBadgeHtml(e) +
                    '<a href="/api/user-imports/export/' + e.id + '" download style="font-size:8px;color:var(--accent-cyan);">' + DROP_PACK_EXT + '</a>' +
                    ' <button type="button" style="font-size:7px;padding:0 4px;background:none;border:1px solid var(--border-color);color:var(--accent-cyan);cursor:pointer;border-radius:3px;" ' +
                    'onclick="copyUserImportShareLink(\'' + e.id + '\',this)">Copy link</button>' +
                    (isPaint ? ' <button type="button" class="btn btn-sm" style="font-size:7px;padding:0 4px;" ' +
                    'onclick="loadUserImportEnginePreview(\'' + e.id + '\',this)">Render</button>' : '') +
                    '</article>';
            }).join('') +
            '</div>';
    }

    function closeUserImportGallery() {
        var modal = document.getElementById('userImportGalleryModal');
        if (modal) modal.style.display = 'none';
    }

    function openUserImportGallery(entries) {
        var list = Array.isArray(entries) ? entries : (window._userImportsGalleryCache || []);
        var modal = document.getElementById('userImportGalleryModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'userImportGalleryModal';
            modal.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,0.82);z-index:10050;overflow:auto;';
            modal.innerHTML =
                '<div style="max-width:920px;margin:24px auto;background:var(--bg-panel,#1a1f28);border:1px solid var(--border-color,#333);border-radius:10px;">' +
                '<div style="display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--border-color,#333);">' +
                '<strong style="font-size:12px;flex:1;">SHOKK DROP</strong>' +
                '<button type="button" class="btn btn-sm" style="font-size:9px;border-color:var(--accent-cyan);color:var(--accent-cyan);" onclick="openCommunityDropsSite()">Browse Community Drops</button>' +
                '<a href="/api/user-imports/export-all" download class="btn btn-sm" style="font-size:9px;border-color:var(--accent-cyan);color:var(--accent-cyan);">Export all' + DROP_PACK_EXT + '</a>' +
                '<button type="button" class="btn btn-sm" style="font-size:9px;" onclick="closeUserImportGallery()">Close</button>' +
                '</div>' +
                '<div id="userImportGalleryDrop" style="margin:8px 12px;padding:10px;border:1px dashed var(--border-color,#444);border-radius:6px;font-size:9px;color:var(--text-dim);text-align:center;">Drop ' + DROP_PACK_EXT + ' pack(s) here</div>' +
                '<div id="userImportGalleryGrid"></div></div>';
            modal.addEventListener('click', function (ev) {
                if (ev.target === modal) closeUserImportGallery();
            });
            document.body.appendChild(modal);
        }
        var grid = document.getElementById('userImportGalleryGrid');
        if (grid) grid.innerHTML = renderGalleryGrid(list);
        bindPackDropZone(document.getElementById('userImportGalleryDrop'), function () {
            openUserImportGalleryFromApi();
        });
        bindPackDropZone(modal.querySelector('div'), function () {
            openUserImportGalleryFromApi();
        });
        modal.style.display = 'block';
    }

    function openUserImportGalleryFromApi() {
        if (typeof openShokkDropLab === 'function') {
            openShokkDropLab();
            return Promise.resolve();
        }
        return fetch('/api/user-imports')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                window._userImportsGalleryCache = data.entries || [];
                openUserImportGallery(window._userImportsGalleryCache);
            })
            .catch(function (err) {
                var toast = (typeof showToast === 'function') ? showToast : function (m) { console.error(m); };
                toast('Gallery failed: ' + err.message, 'error');
            });
    }

    function loadUserImportEnginePreview(id, btn) {
        var card = btn && btn.closest('article');
        var img = card && card.querySelector('img');
        if (!img) return;
        if (btn) btn.textContent = '…';
        img.src = '/api/user-imports/engine-preview/' + id + '?size=512&t=' + Date.now();
        setTimeout(function () { if (btn) btn.textContent = 'Render'; }, 8000);
    }

    window.copyUserImportShareLink = copyUserImportShareLink;
    window.openCommunityDropsSite = openCommunityDropsSite;
    window.openCommunityDropInstall = openCommunityDropInstall;
    window.loadUserImportEnginePreview = loadUserImportEnginePreview;
    window.importUserImportPack = importUserImportPack;
    window.bindUserImportPackDropZone = bindPackDropZone;
    window.openUserImportGallery = openUserImportGalleryFromApi;
    window.closeUserImportGallery = closeUserImportGallery;

    if (window.electronAPI && typeof window.electronAPI.on === 'function') {
        window.electronAPI.on('deep-link', handleCommunityDeepLink);
    }
})();
