(function () {
    'use strict';

    // The Paint Booth runs both as the Electron desktop app and as a plain
    // browser tab (localhost:59876). Wrap the existing in-app picker instead of
    // replacing it. The File Picker setting (Settings > Options) decides which
    // chooser opens for Source Paint / layered paint / iRacing Car Folder:
    //   'shokker' (default) - the in-app Shokker Browser with image previews
    //   'windows'           - Windows File Explorer: the Electron preload bridge
    //                         when it exists, otherwise the server-side dialog
    //                         (POST /api/native-dialog) - the Flask server runs
    //                         on the same desktop, so a browser tab gets the
    //                         real Windows chooser too. [SPB-BETA-2026-09-05]
    var legacyOpenFilePicker = window.openFilePicker;
    if (typeof legacyOpenFilePicker !== 'function' || legacyOpenFilePicker._spbNativeDialogsBridge) return;
    var MAIN_FILE_PICKER_MODE_KEY = 'spb_main_file_picker_mode';

    function normalizeFilePickerMode(mode) {
        return mode === 'windows' ? 'windows' : 'shokker';
    }

    function getMainFilePickerMode() {
        try { return normalizeFilePickerMode(window.localStorage.getItem(MAIN_FILE_PICKER_MODE_KEY)); } catch (_) {}
        return 'shokker';
    }

    // [SPB-BETA-2026-09-05 owner] the two header browse buttons said "in Windows
    // File Explorer" no matter which picker the setting selected - a Shokker
    // Browser user reading that tooltip would conclude the setting is broken.
    function syncHeaderBrowseTooltips() {
        try {
            if (typeof document.querySelector !== 'function') return;
            var where = getMainFilePickerMode() === 'windows'
                ? 'Windows File Explorer'
                : 'the Shokker Browser (image previews)';
            var paint = document.querySelector('[data-testid="btn-browse-paint"]');
            if (paint) {
                paint.title = 'Browse Source Paint in ' + where + ' (TGA, PNG, JPEG, or BMP)';
                paint.setAttribute('aria-label', 'Browse Source Paint in ' + where);
            }
            var folder = document.querySelector('[data-testid="btn-browse-output-dir"]');
            if (folder) {
                folder.title = 'Browse iRacing Car Folder in ' + where;
                folder.setAttribute('aria-label', 'Browse iRacing car folder in ' + where);
            }
        } catch (_) {}
    }

    function syncFilePickerModeControl() {
        try {
            var control = document.getElementById('mainFilePickerMode');
            if (control) control.value = getMainFilePickerMode();
        } catch (_) {}
        syncHeaderBrowseTooltips();
    }

    function ensureFilePickerSettingControl() {
        try {
            if (document.getElementById('mainFilePickerMode')) return;
            var heading = document.getElementById('settingsOptionsHeading');
            var section = heading && (heading.closest ? heading.closest('.settings-section') : heading.parentNode);
            if (!heading || !section || !document.createElement) return;
            var row = document.createElement('div');
            row.className = 'settings-row';
            row.style.cssText = 'flex-direction:column; align-items:flex-start; gap:3px;';
            row.innerHTML =
                '<div style="display:flex; align-items:center; gap:6px; width:100%;">' +
                    '<label for="mainFilePickerMode" style="cursor:pointer; white-space:nowrap;">File Picker</label>' +
                    '<select id="mainFilePickerMode" title="Choose the picker used by Source Paint, layered-paint, and iRacing Folder buttons" ' +
                        'style="flex:1; min-width:0; background:var(--bg-card); border:1px solid var(--border-color); color:var(--text-primary); padding:4px 6px; border-radius:4px; font-size:10px;">' +
                        '<option value="shokker">Shokker Browser — image previews</option>' +
                        '<option value="windows">Windows File Explorer</option>' +
                    '</select>' +
                '</div>' +
                '<div style="font-size:8px; color:var(--text-dim);">Shokker Browser is best for previewing TGA artwork. Windows File Explorer uses the standard Windows chooser. Your choice is saved.</div>';
            var control = row.querySelector('select');
            if (control) control.addEventListener('change', function () { setMainFilePickerMode(control.value); });
            heading.insertAdjacentElement('afterend', row);
        } catch (_) {}
    }

    // SPB-UX-2026-09-03 — owner: users need the preview-friendly Shokker
    // browser for formats such as TGA *and* the familiar Windows chooser.
    // This setting deliberately applies to both header paths and survives
    // relaunches, rather than being a one-off alternate click.
    function setMainFilePickerMode(mode) {
        var next = normalizeFilePickerMode(mode);
        try { window.localStorage.setItem(MAIN_FILE_PICKER_MODE_KEY, next); } catch (_) {}
        syncFilePickerModeControl();
        try {
            if (typeof window.showToast === 'function') {
                window.showToast(next === 'windows'
                    ? 'File picker: Windows File Explorer'
                    : 'File picker: Shokker Browser');
            }
        } catch (_) {}
        return next;
    }

    function selectedPath(result) {
        if (typeof result === 'string') return result.trim();
        if (result && typeof result.filePath === 'string') return result.filePath.trim();
        return '';
    }

    function sourceKind(options) {
        var title = String(options && options.title || '').toLowerCase();
        if (title.indexOf('open layered file') !== -1 || title.indexOf('open layered paint') !== -1) return 'layered';
        if (title.indexOf('select your car paint') !== -1) return 'all';
        if (title.indexOf('select source paint') !== -1 || title.indexOf('choose a source paint') !== -1) return 'flat';
        return '';
    }

    function isIRacingFolderRequest(options) {
        if (!options || options.mode !== 'folder') return false;
        return /(?:select|choose)\s+(?:your\s+)?iracing\s+(?:paint|car)\s+folder/i.test(String(options.title || ''));
    }

    function useLegacy(options, reason) {
        if (reason) {
            try { console.warn('[SPB] Native File Explorer unavailable; using the in-app browser.', reason); } catch (_) {}
        }
        return legacyOpenFilePicker.call(window, options);
    }

    // SPB-UX-2026-09-03 — owner: the paid desktop app must never turn a failed
    // Windows dialog into the old in-app picker. That fallback made the native
    // bridge look unreliable and was materially worse than reporting the error.
    // The legacy picker remains only for a normal browser with no Electron API.
    function reportNativeDialogFailure(error) {
        try { console.error('[SPB] Windows File Explorer could not open.', error); } catch (_) {}
        try {
            if (typeof window.showToast === 'function') {
                var detail = error && error.message ? String(error.message).trim() : '';
                window.showToast('Windows File Explorer could not open. '
                    + (detail || 'Restart Shokker Paint Booth and try again.'), 'error');
            }
        } catch (_) {}
        return null;
    }

    function completeSelection(options, result) {
        var path = selectedPath(result);
        // null/empty is a deliberate Windows-dialog cancel. Opening the legacy
        // picker here would make Cancel look broken by presenting a second UI.
        if (!path) return null;
        if (options && typeof options.onSelect === 'function') return options.onSelect(path);
        return path;
    }

    function finishNativeSelection(options, result) {
        try {
            return Promise.resolve(completeSelection(options, result)).catch(function (error) {
                try { console.error('[SPB] Selected source could not be loaded.', error); } catch (_) {}
                return null;
            });
        } catch (error) {
            try { console.error('[SPB] Selected source could not be loaded.', error); } catch (_) {}
            return Promise.resolve(null);
        }
    }

    // SPB-UX-2026-09-03 (owner: both Main App header buttons must behave exactly
    // like the SHOKK DEMO): expose a direct native-first hook as well as wrapping
    // the legacy picker. Header callers live in the canvas script's own scope,
    // so relying only on the generic global wrapper could leave a stale in-app
    // browser in front of a perfectly available Electron dialog.
    function tryOpenNativeFilePicker(options) {
        var request = options && typeof options === 'object' ? options : {};
        var api = window.electronAPI;
        var kind = sourceKind(request);
        var folderRequest = isIRacingFolderRequest(request);

        if (kind && api) {
            if (typeof api.selectSourcePaint !== 'function') {
                reportNativeDialogFailure(new Error('Native source-paint dialog is unavailable in this desktop build.'));
                return true;
            }
            try {
                Promise.resolve(api.selectSourcePaint(kind, request.startPath || ''))
                    .then(
                        function (result) { return finishNativeSelection(request, result); },
                        reportNativeDialogFailure
                    );
                return true;
            } catch (error) {
                reportNativeDialogFailure(error);
                return true;
            }
        }

        if (folderRequest && api) {
            if (typeof api.selectIRacingCarFolder !== 'function') {
                reportNativeDialogFailure(new Error('Native iRacing-folder dialog is unavailable in this desktop build.'));
                return true;
            }
            try {
                Promise.resolve(api.selectIRacingCarFolder(request.startPath || ''))
                    .then(
                        function (result) { return finishNativeSelection(request, result); },
                        reportNativeDialogFailure
                    );
                return true;
            } catch (error) {
                reportNativeDialogFailure(error);
                return true;
            }
        }

        return false;
    }

    // [SPB-BETA-2026-09-05 owner: "toggle between SHOKKER BROWSER and WINDOWS FILE
    // EXPLORER ... It's showing up in Settings but nothing changes when you try to
    // change it to FILE EXPLORER"]. Root cause: 'windows' mode could only reach a
    // dialog through the Electron preload bridge. In a plain browser tab
    // (localhost:59876 - how the owner runs the app) window.electronAPI does not
    // exist, so tryOpenNativeFilePicker returned false and the setting fell
    // straight back to the Shokker Browser. The Flask server runs on the same
    // desktop, so it now opens the real Windows chooser itself
    // (POST /api/native-dialog in server_routes/file_picker_routes.py) and returns
    // the chosen path. Failures are reported, never silently swapped for the
    // in-app picker (owner mandate 2026-09-03).
    function isWindowsDialogCandidate(request) {
        return !!sourceKind(request) || isIRacingFolderRequest(request);
    }

    function openServerNativeDialog(request) {
        if (typeof window.fetch !== 'function') {
            reportNativeDialogFailure(new Error('This browser cannot reach the Shokker Paint Booth dialog service.'));
            return true;
        }
        var body = {
            mode: request.mode === 'folder' ? 'folder' : 'file',
            title: String(request.title || ''),
            filter: String(request.filter || ''),
            startPath: String(request.startPath || '')
        };
        try {
            window.fetch('/api/native-dialog', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Shokker-Internal': '1' },
                body: JSON.stringify(body)
            }).then(function (response) {
                return response.json().catch(function () { return {}; }).then(function (payload) {
                    payload = payload || {};
                    if (!response.ok || payload.success === false) {
                        throw new Error(payload.error || ('the server replied HTTP ' + response.status));
                    }
                    // A cancelled dialog is a deliberate "no" - never open a second UI.
                    if (payload.cancelled || !payload.path) return null;
                    return finishNativeSelection(request, payload.path);
                });
            }).then(null, reportNativeDialogFailure);
        } catch (error) {
            reportNativeDialogFailure(error);
        }
        return true;
    }

    // 'windows' mode: Electron bridge first, server-side dialog in a browser tab.
    function openWindowsFilePicker(request) {
        if (tryOpenNativeFilePicker(request)) return true;
        return openServerNativeDialog(request);
    }

    // Generic window.openFilePicker wrapper (Easy Mode, recipes, etc.). Only the
    // Source Paint / layered / iRacing-folder pickers are eligible for Windows
    // File Explorer, and - since 2026-09-05 - they follow the same saved setting
    // as the header buttons instead of forcing the Electron dialog.
    function nativeAwareOpenFilePicker(options) {
        var request = options && typeof options === 'object' ? options : {};
        if (!isWindowsDialogCandidate(request)) return useLegacy(request);
        if (getMainFilePickerMode() !== 'windows') return useLegacy(request);
        return openWindowsFilePicker(request);
    }

    function openMainFilePicker(request) {
        if (getMainFilePickerMode() !== 'windows') return useLegacy(request);
        return openWindowsFilePicker(request);
    }

    function startDirectory(inputId) {
        var value = '';
        try { value = String((document.getElementById(inputId) || {}).value || '').trim(); } catch (_) {}
        return value.replace(/[/\\][^/\\]+$/, '');
    }

    function selectMainSourcePaint() {
        var request = {
            title: 'Choose a Source Paint',
            filter: '.tga,.png,.jpg,.jpeg,.bmp',
            mode: 'file',
            startPath: startDirectory('paintFile'),
            onSelect: function (path) {
                return typeof window.loadPaintPreviewFromServer === 'function'
                    ? window.loadPaintPreviewFromServer(path)
                    : null;
            }
        };
        return openMainFilePicker(request);
    }

    function selectMainIRacingFolder() {
        var request = {
            title: 'Choose your iRacing Car Folder',
            filter: '',
            mode: 'folder',
            startPath: startDirectory('outputDir'),
            onSelect: function (path) {
                var output = document.getElementById('outputDir');
                if (!output) return null;
                output.value = path;
                if (typeof window.updateOutputPath === 'function') window.updateOutputPath();
                if (typeof window.showToast === 'function') window.showToast('iRacing folder set!');
                return path;
            }
        };
        return openMainFilePicker(request);
    }

    function selectMainLayeredPaint() {
        var request = {
            title: 'Open Layered Paint',
            filter: '.psd,.ora,.xcf',
            mode: 'file',
            startPath: startDirectory('paintFile'),
            onSelect: function (path) {
                return typeof window.importPSDFromPath === 'function'
                    ? window.importPSDFromPath(path)
                    : null;
            }
        };
        return openMainFilePicker(request);
    }

    nativeAwareOpenFilePicker._spbNativeDialogsBridge = true;
    nativeAwareOpenFilePicker._spbLegacyOpenFilePicker = legacyOpenFilePicker;
    window.tryOpenNativeFilePicker = tryOpenNativeFilePicker;
    window.openServerNativeDialog = openServerNativeDialog;
    window.getMainFilePickerMode = getMainFilePickerMode;
    window.setMainFilePickerMode = setMainFilePickerMode;
    window.selectMainSourcePaint = selectMainSourcePaint;
    window.selectMainIRacingFolder = selectMainIRacingFolder;
    window.selectMainLayeredPaint = selectMainLayeredPaint;
    window.openFilePicker = nativeAwareOpenFilePicker;
    function initializeFilePickerPreference() {
        ensureFilePickerSettingControl();
        syncFilePickerModeControl();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeFilePickerPreference, { once: true });
    } else {
        initializeFilePickerPreference();
    }
}());
