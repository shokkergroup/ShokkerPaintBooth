"""Filesystem picker and path validation routes for Shokker Paint Booth."""

import base64
import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile
import threading
from collections import OrderedDict

from flask import jsonify, request, send_file
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


# [SPB-BETA-2026-09-05] PowerShell source for /api/native-dialog (see the route below).
# Module-level so tests/test_native_dialog_route.py can run the real script.
NATIVE_DIALOG_PS = r'''
$ErrorActionPreference = 'Stop'
$outFile = [string]$env:SPB_DLG_OUT
function Emit([string]$line) {
    if ($outFile) {
        [System.IO.File]::WriteAllText($outFile, $line, (New-Object System.Text.UTF8Encoding($false)))
    }
    Write-Output $line
}
$owner = $null
try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [System.Windows.Forms.Application]::EnableVisualStyles()
    $mode   = [string]$env:SPB_DLG_MODE
    $title  = [string]$env:SPB_DLG_TITLE
    $start  = [string]$env:SPB_DLG_START
    $filter = [string]$env:SPB_DLG_FILTER

    # Invisible top-most owner so the chooser opens ABOVE the browser window
    # instead of behind it (the server process is not the foreground app).
    # The chooser opens with its top-left at the owner's position, so the owner
    # sits half a typical dialog (960x540 measured at 1920x1080) up-left of the
    # primary screen's centre. An owner parked OFF-screen put the chooser
    # off-screen too - that exact bug hung the first end-to-end run 2026-09-05.
    $owner = New-Object System.Windows.Forms.Form
    $owner.Text = 'Shokker Paint Booth'
    $owner.TopMost = $true
    $owner.ShowInTaskbar = $false
    $owner.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
    $owner.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
    $area = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
    $ox = [Math]::Max($area.Left, $area.Left + [int]($area.Width / 2) - 480)
    $oy = [Math]::Max($area.Top, $area.Top + [int]($area.Height / 2) - 270)
    $owner.Location = New-Object System.Drawing.Point($ox, $oy)
    $owner.Size = New-Object System.Drawing.Size(1, 1)
    $owner.Opacity = 0
    $owner.Show()
    $owner.Activate()
    [System.Windows.Forms.Application]::DoEvents()

    if ($mode -eq 'folder') {
        $src = @'
using System;
using System.Runtime.InteropServices;
namespace SpbDlg
{
    [ComImport, Guid("43826d1e-e718-42ee-bc55-a1e261c37bfe"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IShellItem
    {
        void BindToHandler(IntPtr pbc, ref Guid bhid, ref Guid riid, out IntPtr ppv);
        void GetParent(out IShellItem ppsi);
        void GetDisplayName(uint sigdnName, [MarshalAs(UnmanagedType.LPWStr)] out string ppszName);
        void GetAttributes(uint sfgaoMask, out uint psfgaoAttribs);
        void Compare(IShellItem psi, uint hint, out int piOrder);
    }
    [ComImport, Guid("42f85136-db7e-439c-85f1-e4075d135fc8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IFileDialog
    {
        [PreserveSig] int Show(IntPtr parent);
        void SetFileTypes(uint cFileTypes, IntPtr rgFilterSpec);
        void SetFileTypeIndex(uint iFileType);
        void GetFileTypeIndex(out uint piFileType);
        void Advise(IntPtr pfde, out uint pdwCookie);
        void Unadvise(uint dwCookie);
        void SetOptions(uint fos);
        void GetOptions(out uint pfos);
        void SetDefaultFolder(IShellItem psi);
        void SetFolder(IShellItem psi);
        void GetFolder(out IShellItem ppsi);
        void GetCurrentSelection(out IShellItem ppsi);
        void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string pszName);
        void GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string pszName);
        void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string pszTitle);
        void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string pszText);
        void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string pszLabel);
        void GetResult(out IShellItem ppsi);
        void AddPlace(IShellItem psi, int fdap);
        void SetDefaultExtension([MarshalAs(UnmanagedType.LPWStr)] string pszDefaultExtension);
        void Close(int hr);
        void SetClientGuid(ref Guid guid);
        void ClearClientData();
        void SetFilter(IntPtr pFilter);
    }
    [ComImport, Guid("DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7")]
    public class FileOpenDialogRCW { }
    public static class FolderPicker
    {
        [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
        private static extern void SHCreateItemFromParsingName([MarshalAs(UnmanagedType.LPWStr)] string pszPath, IntPtr pbc, ref Guid riid, [MarshalAs(UnmanagedType.Interface)] out IShellItem ppv);
        public static string Pick(IntPtr owner, string title, string startPath)
        {
            IFileDialog dlg = (IFileDialog)new FileOpenDialogRCW();
            uint options;
            dlg.GetOptions(out options);
            // FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST | FOS_NOCHANGEDIR
            dlg.SetOptions(options | 0x20u | 0x40u | 0x800u | 0x8u);
            if (!string.IsNullOrEmpty(title)) dlg.SetTitle(title);
            dlg.SetOkButtonLabel("Select Folder");
            if (!string.IsNullOrEmpty(startPath) && System.IO.Directory.Exists(startPath))
            {
                try
                {
                    Guid iid = typeof(IShellItem).GUID;
                    IShellItem folder;
                    SHCreateItemFromParsingName(startPath, IntPtr.Zero, ref iid, out folder);
                    dlg.SetFolder(folder);
                }
                catch { }
            }
            int hr = dlg.Show(owner);
            if (hr != 0) return null;   // includes ERROR_CANCELLED
            IShellItem item;
            dlg.GetResult(out item);
            string path;
            item.GetDisplayName(0x80058000u, out path);   // SIGDN_FILESYSPATH
            return path;
        }
    }
}
'@
        $picked = $null
        $modern = $true
        try {
            Add-Type -TypeDefinition $src -Language CSharp
        } catch {
            $modern = $false
        }
        if ($modern) {
            $picked = [SpbDlg.FolderPicker]::Pick($owner.Handle, $title, $start)
            if ($picked) { Emit ('PATH:' + $picked) } else { Emit 'CANCEL' }
        } else {
            # Modern picker unavailable on this machine: classic Windows folder tree.
            $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
            $dlg.Description = $title
            $dlg.ShowNewFolderButton = $true
            if ($start -and (Test-Path -LiteralPath $start -PathType Container)) { $dlg.SelectedPath = $start }
            $res = $dlg.ShowDialog($owner)
            if ($res -eq [System.Windows.Forms.DialogResult]::OK -and $dlg.SelectedPath) { Emit ('PATH:' + $dlg.SelectedPath) } else { Emit 'CANCEL' }
        }
    } else {
        $dlg = New-Object System.Windows.Forms.OpenFileDialog
        $dlg.Title = $title
        if ($filter) { $dlg.Filter = $filter }
        $dlg.Multiselect = $false
        $dlg.CheckFileExists = $true
        $dlg.CheckPathExists = $true
        $dlg.RestoreDirectory = $true
        $dlg.DereferenceLinks = $true
        if ($start -and (Test-Path -LiteralPath $start -PathType Container)) { $dlg.InitialDirectory = $start }
        $res = $dlg.ShowDialog($owner)
        if ($res -eq [System.Windows.Forms.DialogResult]::OK -and $dlg.FileName) { Emit ('PATH:' + $dlg.FileName) } else { Emit 'CANCEL' }
    }
} catch {
    Emit ('ERROR:' + $_.Exception.Message)
} finally {
    if ($owner) { try { $owner.Close(); $owner.Dispose() } catch { } }
}
'''


def register_file_picker_routes(app, *, load_config, logger, external_write_guard=None):
    """Register source-paint file browser routes."""

    @app.route('/check-file', methods=['POST'])
    def check_file():
        """Check whether a file path exists on disk."""
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "Invalid or missing JSON body"}), 400
            if 'path' not in data:
                return jsonify({"error": "Missing 'path' field in request"}), 400
            path = data['path']
            logger.debug(f"[check-file] Checking: {path}")
            exists = os.path.exists(path)
            is_file = os.path.isfile(path) if exists else False
            size = os.path.getsize(path) if is_file else 0
            return jsonify({
                "path": path,
                "exists": exists,
                "is_file": is_file,
                "size": size,
                "size_human": f"{size / 1024:.0f} KB" if size > 0 else "0",
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # [SPB-QOL 2026-08-06, owner ask] Tiny square thumbnails for the file
    # picker, so a painter picking a paint can SEE the cars instead of reading
    # filenames. Disk-cached by (absolute path, mtime, size, thumb size): a
    # repeat browse of the same folder costs one small file read per entry, not
    # a TGA decode. PIL opens TGA/PNG/JPG/BMP natively; PSD is intentionally
    # excluded (PIL's PSD support is partial and a wrong-looking thumbnail is
    # worse than none — the picker falls back to the plain icon).
    #
    # NOTE this module (not server.py) is where the endpoint must live: the
    # picker's routes are registered here, and a first attempt to anchor the
    # route in server.py silently landed nowhere because the only match for
    # "@app.route('/browse-files'" in that file is a DOCSTRING mention.
    _thumb_cache_dir = os.path.join(tempfile.gettempdir(), 'shokker_file_thumbs')
    # [2026-08-06 owner ask] PSD included: PIL reads the flattened composite
    # most PSDs embed. Files without one fail the open — the endpoint 500s and
    # the picker's onerror collapses that row back to the plain icon, so a bad
    # PSD degrades to exactly the old look instead of a wrong image.
    _thumb_exts = {'.tga', '.png', '.jpg', '.jpeg', '.bmp', '.psd'}
    _approved_thumb_paths = OrderedDict()
    _approved_thumb_paths_lock = threading.Lock()
    _approved_thumb_paths_limit = 4096

    def _approve_thumb_files(items):
        with _approved_thumb_paths_lock:
            for item in items:
                candidate = item.get("path") if isinstance(item, dict) and item.get("type") == "file" else None
                if not candidate or os.path.splitext(candidate)[1].lower() not in _thumb_exts:
                    continue
                canonical = os.path.realpath(os.path.abspath(os.path.normpath(candidate)))
                _approved_thumb_paths[canonical] = None
                _approved_thumb_paths.move_to_end(canonical)
            while len(_approved_thumb_paths) > _approved_thumb_paths_limit:
                _approved_thumb_paths.popitem(last=False)

    def _thumb_path_is_approved(path):
        canonical = os.path.realpath(os.path.abspath(os.path.normpath(path)))
        with _approved_thumb_paths_lock:
            if canonical not in _approved_thumb_paths:
                return False
            _approved_thumb_paths.move_to_end(canonical)
        return True

    @app.route('/api/file-thumb')
    def file_thumb():
        raw_path = (request.args.get('path') or '').strip()
        try:
            size = max(24, min(512, int(request.args.get('size', 48))))   # 512 cap: grid tiles ask for 320
        except (TypeError, ValueError):
            size = 48
        if not raw_path:
            return jsonify({"error": "path required"}), 400
        path = os.path.realpath(os.path.abspath(os.path.normpath(raw_path)))
        ext = os.path.splitext(path)[1].lower()
        if ext not in _thumb_exts:
            return jsonify({"error": "unsupported type"}), 415
        if not _thumb_path_is_approved(path):
            return jsonify({"error": "thumbnail path not approved by file picker"}), 403
        if not os.path.isfile(path):
            return jsonify({"error": "not found"}), 404
        try:
            st = os.stat(path)
            key = hashlib.sha1(
                f"{os.path.abspath(path)}|{st.st_mtime_ns}|{st.st_size}|{size}".encode('utf-8', 'ignore')
            ).hexdigest()
            cached = os.path.join(_thumb_cache_dir, key + '.png')
            denial = (external_write_guard(cached, "file-thumbnail-cache")
                      if external_write_guard is not None else None)
            if denial:
                from PIL import Image
                with Image.open(path) as im:
                    im = im.convert('RGB')
                    w, h = im.size
                    edge = min(w, h)
                    left = (w - edge) // 2
                    top = (h - edge) // 2
                    im = im.crop((left, top, left + edge, top + edge))
                    im.thumbnail((size, size), Image.Resampling.BILINEAR)
                    buffer = io.BytesIO()
                    im.save(buffer, 'PNG', compress_level=6)
                buffer.seek(0)
                resp = send_file(buffer, mimetype='image/png')
                resp.headers['Cache-Control'] = 'no-store'
                return resp
            os.makedirs(_thumb_cache_dir, exist_ok=True)
            if not os.path.isfile(cached):
                from PIL import Image
                with Image.open(path) as im:
                    im = im.convert('RGB')
                    # centre square crop: livery sheets are square already, and
                    # for odd aspect ratios the middle beats letterboxing at 48px
                    w, h = im.size
                    edge = min(w, h)
                    left = (w - edge) // 2
                    top = (h - edge) // 2
                    im = im.crop((left, top, left + edge, top + edge))
                    im.thumbnail((size, size), Image.Resampling.BILINEAR)
                    im.save(cached, 'PNG', compress_level=6)
            resp = send_file(cached, mimetype='image/png')
            resp.headers['Cache-Control'] = 'public, max-age=86400'
            return resp
        except Exception as e:
            logger.debug(f"[file-thumb] failed for {path}: {e}")
            return jsonify({"error": "thumbnail failed"}), 500

    @app.route('/browse-files', methods=['POST'])
    def browse_files():
        """Browse filesystem directories for the UI file picker."""
        try:
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            logger.debug(f"[browse-files] path={data.get('path', '(root)')}")
            browse_path = data.get('path', '')
            file_filter = data.get('filter', '').lower()
            # [2026-07-04] filter accepts a comma list ('.psd,.ora') — str.endswith
            # takes a tuple, so multi-extension pickers cost nothing extra.
            if ',' in file_filter:
                file_filter = tuple(x.strip() for x in file_filter.split(',') if x.strip())

            if not browse_path:
                drives = []
                for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                    drive = f"{letter}:/"
                    if os.path.exists(drive):
                        drives.append({"name": f"{letter}:", "path": drive, "type": "drive"})
                user_home = os.path.expanduser("~")
                quick_navs = []
                iracing_paint = os.path.join(user_home, "Documents", "iRacing", "paint")
                if os.path.isdir(iracing_paint):
                    quick_navs.append({"name": "iRacing Paint Folder", "path": iracing_paint.replace("\\", "/"), "type": "shortcut"})
                cfg = load_config()
                for car_name, car_path in cfg.get("car_paths", {}).items():
                    if os.path.isdir(car_path):
                        quick_navs.append({"name": f"Live Link: {car_name}", "path": car_path.replace("\\", "/"), "type": "shortcut"})
                return jsonify({"path": "", "drives": drives, "quick_navs": quick_navs, "items": []})

            browse_path = os.path.normpath(browse_path)
            if not os.path.isdir(browse_path):
                return jsonify({"error": f"Not a directory: {browse_path}"}), 400

            max_files = 200
            large_dir_threshold = 300
            folders = []
            files = []
            total_files = 0
            entry_count = 0

            fast_folders = None
            try:
                r = subprocess.run(
                    ['cmd', '/c', 'dir', '/b', '/ad', browse_path],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                if r.returncode == 0 and r.stdout.strip():
                    fast_folders = []
                    for nm in [n.strip() for n in r.stdout.splitlines() if n.strip()]:
                        if nm.startswith('.'):
                            continue
                        fp = os.path.join(browse_path, nm).replace("\\", "/")
                        fast_folders.append({"name": nm, "path": fp, "type": "folder"})
            except Exception:
                fast_folders = None

            if fast_folders is not None:
                try:
                    r2 = subprocess.run(
                        ['cmd', '/c', 'dir', '/b', browse_path],
                        capture_output=True,
                        text=True,
                        timeout=8,
                    )
                    entry_count = len(r2.stdout.strip().splitlines()) if r2.returncode == 0 and r2.stdout.strip() else 0
                except Exception:
                    entry_count = len(fast_folders) + 500

                if entry_count > large_dir_threshold:
                    folders = sorted(fast_folders, key=lambda x: x["name"].lower())
                    parent = os.path.dirname(browse_path)
                    parent_path = parent.replace("\\", "/") if parent != browse_path else ""
                    return jsonify({
                        "path": browse_path.replace("\\", "/"),
                        "parent": parent_path,
                        "items": folders,
                        "total_folders": len(folders),
                        "total_files": 0,
                        "hidden_files": -1,
                        "large_dir": True,
                        "entry_count": entry_count,
                    })

            try:
                with os.scandir(browse_path) as scanner:
                    for entry in scanner:
                        if entry.name.startswith('.'):
                            continue
                        entry_count += 1
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                folders.append({"name": entry.name, "path": entry.path.replace("\\", "/"), "type": "folder"})
                            else:
                                if file_filter and not entry.name.lower().endswith(file_filter):
                                    continue
                                total_files += 1
                                if len(files) < max_files:
                                    try:
                                        size = entry.stat(follow_symlinks=False).st_size
                                    except OSError:
                                        size = 0
                                    files.append({
                                        "name": entry.name,
                                        "path": entry.path.replace("\\", "/"),
                                        "type": "file",
                                        "size": size,
                                        "size_human": f"{size / 1024:.0f} KB" if size > 0 else "0",
                                    })
                        except OSError as _spb_ex:
                            _spb_swallow('browse_files@L258', _spb_ex); continue
            except PermissionError:
                return jsonify({"error": "Permission denied", "path": browse_path}), 403

            hidden_files = total_files - len(files)
            folders.sort(key=lambda x: x["name"].lower())
            files.sort(key=lambda x: x["name"].lower())
            _approve_thumb_files(files)
            parent = os.path.dirname(browse_path)
            parent_path = parent.replace("\\", "/") if parent != browse_path else ""
            return jsonify({
                "path": browse_path.replace("\\", "/"),
                "parent": parent_path,
                "items": folders + files,
                "total_folders": len(folders),
                "total_files": total_files,
                "hidden_files": hidden_files,
                "large_dir": False,
                "entry_count": entry_count,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ------------------------------------------------------------------
    # [SPB-BETA-2026-09-05 owner: "toggle between SHOKKER BROWSER and WINDOWS
    # FILE EXPLORER ... It's showing up in Settings but nothing changes when you
    # try to change it to FILE EXPLORER"]
    #
    # The File Picker setting could only reach a Windows dialog through the
    # Electron preload bridge (dialog.showOpenDialog). In a plain browser tab -
    # which is how the owner runs the app at localhost:59876 - there is no
    # bridge, so 'windows' mode silently fell back to the in-app picker. This
    # server runs on the same desktop as the browser, so it can open the real
    # Windows chooser itself: WinForms OpenFileDialog for files and the modern
    # IFileOpenDialog (FOS_PICKFOLDERS - the same Explorer-style folder picker
    # Electron shows) for folders, in an STA PowerShell child. The request
    # thread blocks while the dialog is open (Werkzeug is threaded, other
    # requests keep flowing); one dialog at a time; the result comes back via a
    # UTF-8 temp file so non-ASCII paths survive the console code page.
    # Client: js/spb-native-file-dialogs.js openServerNativeDialog().
    _native_dialog_lock = threading.Lock()
    _native_dialog_ext_re = re.compile(r'^[a-z0-9]{1,8}$')
    _NATIVE_DIALOG_TIMEOUT_S = 15 * 60

    _NATIVE_DIALOG_PS = NATIVE_DIALOG_PS  # module-level so tests can exercise the PowerShell source directly

    def _native_dialog_extensions(raw):
        """'.tga,.png' / '*.tga;*.png' -> ['tga', 'png'] (validated, deduped)."""
        exts = []
        for part in str(raw or '').replace(';', ',').split(','):
            part = part.strip().lower().lstrip('*').lstrip('.')
            if part and _native_dialog_ext_re.match(part) and part not in exts:
                exts.append(part)
        return exts

    def _native_dialog_filter(exts):
        if not exts:
            return 'All files (*.*)|*.*'
        pattern = ';'.join('*.' + e for e in exts)
        return 'Paint files (' + pattern + ')|' + pattern

    def _powershell_exe():
        candidate = os.path.join(
            os.environ.get('SystemRoot', r'C:\Windows'),
            'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
        return candidate if os.path.isfile(candidate) else 'powershell.exe'

    @app.route('/api/native-dialog', methods=['POST'])
    def api_native_dialog():
        """Open the real Windows file/folder chooser from the server process.

        JSON: ``{mode: 'file'|'folder', title, filter: '.tga,.png', startPath}``.
        Replies ``{success, cancelled, path}``; a cancelled dialog is success with
        ``cancelled: true`` so the client never opens a second picker."""
        if request.headers.get('X-Shokker-Internal') != '1':
            return jsonify({"success": False, "error": "Blocked: missing SPB internal request header"}), 403
        if not sys.platform.startswith('win'):
            return jsonify({"success": False, "error": "Windows File Explorer dialogs are only available on Windows."}), 501
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400
        mode = 'folder' if str(data.get('mode') or '').lower() == 'folder' else 'file'
        title = re.sub(r'[\r\n\t]+', ' ', str(data.get('title') or '')).strip()[:120]
        if not title:
            title = 'Choose your iRacing Car Folder' if mode == 'folder' else 'Choose a Source Paint'
        exts = _native_dialog_extensions(data.get('filter')) if mode == 'file' else []
        start = str(data.get('startPath') or '').strip()[:4096]
        if start:
            start = os.path.normpath(start)
            if os.path.isfile(start):
                start = os.path.dirname(start)
            if not os.path.isdir(start):
                start = ''

        if not _native_dialog_lock.acquire(blocking=False):
            return jsonify({"success": False, "error": "A Windows File Explorer window is already open. Finish or cancel it first."}), 409
        out_path = None
        try:
            fd, out_path = tempfile.mkstemp(prefix='spb_native_dialog_', suffix='.txt')
            os.close(fd)
            env = os.environ.copy()
            env.update({
                'SPB_DLG_MODE': mode,
                'SPB_DLG_TITLE': title,
                'SPB_DLG_START': start,
                'SPB_DLG_FILTER': _native_dialog_filter(exts) if mode == 'file' else '',
                'SPB_DLG_OUT': out_path,
            })
            encoded = base64.b64encode(_NATIVE_DIALOG_PS.encode('utf-16-le')).decode('ascii')
            cmd = [_powershell_exe(), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                   '-STA', '-WindowStyle', 'Hidden', '-EncodedCommand', encoded]
            logger.info(f"[native-dialog] opening Windows {mode} dialog (start={start or '(default)'})")
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=_NATIVE_DIALOG_TIMEOUT_S,
                    env=env,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                )
            except subprocess.TimeoutExpired:
                return jsonify({"success": False, "error": "The Windows File Explorer window was left open too long and was closed."}), 504
            except OSError as e:
                return jsonify({"success": False, "error": f"Windows File Explorer could not be started: {e}"}), 500

            result = ''
            try:
                with open(out_path, 'r', encoding='utf-8-sig') as fh:
                    result = fh.read().strip()
            except OSError:
                result = ''
            if not result:
                stdout_lines = (proc.stdout or b'').decode('utf-8', 'replace').strip().splitlines()
                result = next((ln.strip() for ln in reversed(stdout_lines)
                               if ln.strip().startswith(('PATH:', 'CANCEL', 'ERROR:'))), '')

            if result == 'CANCEL':
                return jsonify({"success": True, "cancelled": True, "mode": mode, "path": None})
            if not result.startswith('PATH:'):
                if result.startswith('ERROR:'):
                    detail = result[6:].strip()
                else:
                    err_lines = (proc.stderr or b'').decode('utf-8', 'replace').strip().splitlines()
                    detail = err_lines[-1].strip() if err_lines else f'no result (exit {proc.returncode})'
                logger.error(f"[native-dialog] PowerShell dialog failed (rc={proc.returncode}): {detail[:300]}")
                return jsonify({"success": False, "error": f"Windows File Explorer could not open: {detail[:200]}"}), 500

            picked = os.path.normpath(result[5:].strip())
            if mode == 'folder':
                if not os.path.isdir(picked):
                    return jsonify({"success": False, "error": "The selected iRacing destination is not a folder."}), 400
            else:
                ext = os.path.splitext(picked)[1].lstrip('.').lower()
                if not os.path.isfile(picked) or (exts and ext not in exts):
                    return jsonify({"success": False, "error": "The selected paint is not a supported source file."}), 400
            return jsonify({"success": True, "cancelled": False, "mode": mode, "path": picked})
        finally:
            if out_path:
                try:
                    os.remove(out_path)
                except OSError as cleanup_error:
                    logger.debug(f"[native-dialog] temp result file not removed: {cleanup_error}")
            _native_dialog_lock.release()
