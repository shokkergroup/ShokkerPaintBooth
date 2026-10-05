"""SPB support: read-only facts about the buyer's iRacing paint folder  (2026-10-02, "Talk to Shokker" troubleshooter).

POST /api/support/folder-probe   {folder, iracing_id, custom_number, paint_file}
  -> {ok, folder:{...}, files:[...], expected:{...}, found:{...}, mips:{...}, ids_in_folder:[...], paint_file:{...}}
POST /api/support/show-files     {folder?, job_id?, select?}  (2026-10-04 "Show my files" on the render result)
  -> opens an Explorer window on the folder the render wrote to, with the paint file highlighted; {ok, path, selected}

It only STATS paths and lists NAMES (never reads file contents), only for paths the buyer typed into the app's own header fields, POST only, loopback host only,
same local-origin guard as the other AI routes. Hardening after the 2026-10-02 review: UNC paths (\\\\host\\share) are never touched (a stat on one blocks a worker and starts SMB auth),
network drives are skipped, the whole probe is time-boxed, the buyer's own files are stat'ed BY NAME (a Trading Paints folder holds hundreds of car_<id>.tga files and a capped listing missed them).
It answers the questions a support person would ask first: does the car folder exist, is it a folder (not a .tga), is it an iRacing paint folder, are the files the app should have written there
(car_num_<id>.tga or car_<id>.tga, plus car_spec_<id>.tga), how old are they, are there files for the other naming scheme.
"""
from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _Timeout

_PAINT_NAME = re.compile(r'^(car|helmet|suit)(_num|_spec|_team|_decal|_decal_num)?(_team)?_?([0-9]{3,9})?\.(tga|mip|png|jpg)$', re.I)
_ID_FILE = re.compile(r'^car_(num_|spec_|team_)?([0-9]{3,9})\.(tga|mip)$', re.I)
_SCAN_MAX = 20000          # entries looked at (names only); the listing sent back is capped separately
_SCAN_SECONDS = 2.5
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix='spb-support-probe')


def _kind(name: str) -> str:
    n = name.lower()
    if n.startswith('car_spec_'):
        return 'spec'
    if n.startswith('car_num_'):
        return 'num'
    if n.startswith('car_team_'):
        return 'team'
    if re.match(r'^car_[0-9]{3,9}\.(tga|mip)$', n):
        return 'diffuse'
    if n.startswith('helmet'):
        return 'helmet'
    if n.startswith('suit'):
        return 'suit'
    return 'other'


def _is_unc(p: str) -> bool:
    q = p.replace('/', '\\')
    return q.startswith('\\\\')


def _drive_is_remote(drive_root: str) -> bool:
    """True for a mapped network drive (a stat on a dead one can hang for a long time)."""
    try:
        import ctypes
        return ctypes.windll.kernel32.GetDriveTypeW(drive_root) == 4      # DRIVE_REMOTE
    except Exception:
        return False


def _stat_name(folder: str, name: str):
    try:
        st = os.stat(os.path.join(folder, name))
        return {'name': name, 'size': st.st_size, 'mtime': st.st_mtime}
    except OSError:
        return None


def _probe(folder: str, iracing_id: str, custom_number: bool, paint_file: str) -> dict:
    out = {'ok': True, 'checked_at': time.time()}
    f = str(folder or '').strip().strip('"')
    info = {'given': f, 'exists': False, 'is_dir': False, 'is_file': False, 'ends_with_tga': bool(re.search(r'\.(tga|mip|psd)$', f, re.I)),
            'writable': None, 'name': '', 'parent_name': '', 'in_iracing_paint': False, 'under_onedrive': False, 'drive_exists': True,
            'unc': False, 'remote_drive': False, 'is_paint_root': False, 'is_gear_folder': False, 'parent_dir': '', 'parent_is_dir': False}
    skip_stat = False
    if f:
        norm = f.replace('/', '\\')
        low = norm.lower()
        info['in_iracing_paint'] = bool(re.search(r'\\iracing\\paint(\\|$)', low))
        info['under_onedrive'] = 'onedrive' in low
        info['name'] = os.path.basename(norm.rstrip('\\'))
        info['parent_name'] = os.path.basename(os.path.dirname(norm.rstrip('\\')))
        info['is_paint_root'] = bool(re.search(r'\\iracing\\paint\\?$', low))
        info['is_gear_folder'] = bool(re.match(r'^(helmets?|suits?|gloves?|shoes?)$', info['name'], re.I))
        info['parent_dir'] = os.path.dirname(norm.rstrip('\\'))
        if _is_unc(norm):
            info['unc'] = True
            skip_stat = True
        else:
            m = re.match(r'^([a-zA-Z]):\\', norm)
            if m:
                root = m.group(1) + ':\\'
                if _drive_is_remote(root):
                    info['remote_drive'] = True
                    skip_stat = True
                else:
                    info['drive_exists'] = os.path.exists(root)
                    if not info['drive_exists']:
                        skip_stat = True
        if not skip_stat:
            try:
                info['exists'] = os.path.exists(f)
                info['is_dir'] = os.path.isdir(f)
                info['is_file'] = os.path.isfile(f)
                if info['is_dir']:
                    info['writable'] = os.access(f, os.W_OK)      # informational only: on Windows this ignores the read-only attribute and ACLs
                # server.py coerces a path that is not a folder to its parent folder and reports success: say where the files would REALLY go
                if not info['is_dir'] and info['parent_dir'] and os.path.isdir(info['parent_dir']):
                    info['parent_is_dir'] = True
            except Exception:
                pass
    out['folder'] = info

    rid = re.sub(r'\D', '', str(iracing_id or ''))
    paint_name = ('car_num_%s.tga' if custom_number else 'car_%s.tga') % rid if rid else None
    other_name = ('car_%s.tga' if custom_number else 'car_num_%s.tga') % rid if rid else None
    spec_name = ('car_spec_%s.tga' % rid) if rid else None
    scan_dir = f if info['is_dir'] else (info['parent_dir'] if info['parent_is_dir'] else None)
    out['scanned_parent'] = bool(scan_dir and not info['is_dir'])

    # 1. the buyer's own files, by name (never lost to a cap)
    by_name = {}
    if scan_dir and rid:
        for nm in (paint_name, other_name, spec_name, 'car_spec_%s.mip' % rid, 'car_num_%s.mip' % rid, 'car_%s.mip' % rid):
            hit = _stat_name(scan_dir, nm)
            if hit:
                by_name[nm.lower()] = hit

    # 2. a names-only look at the folder for the listing and the other IDs (bounded in entries and time)
    files, ids, scanned, t0 = [], {}, 0, time.time()
    if scan_dir:
        try:
            with os.scandir(scan_dir) as it:
                for e in it:
                    scanned += 1
                    if scanned > _SCAN_MAX or time.time() - t0 > _SCAN_SECONDS:
                        out['scan_truncated'] = True
                        break
                    if not _PAINT_NAME.match(e.name):
                        continue
                    mm = _ID_FILE.match(e.name)
                    if mm:
                        ids[mm.group(2)] = ids.get(mm.group(2), 0) + 1
                    if len(files) < 400:
                        try:
                            st = e.stat()
                        except OSError:
                            continue
                        files.append({'name': e.name, 'size': st.st_size, 'mtime': st.st_mtime, 'kind': _kind(e.name), 'id': mm.group(2) if mm else None})
        except OSError as ex:
            out['list_error'] = str(ex)[:120]
    files.sort(key=lambda x: -x['mtime'])
    out['files'] = files[:60]
    out['ids_in_folder'] = sorted(ids.keys())[:40]
    out['ids_in_folder_count'] = len(ids)
    out['expected'] = {'paint': paint_name, 'spec': spec_name, 'other_scheme': other_name}
    g = lambda n: by_name.get(n.lower()) if n else None
    out['found'] = {
        'paint': bool(g(paint_name)),
        'spec': bool(g(spec_name) or (rid and g('car_spec_%s.mip' % rid))),
        'other_scheme': bool(g(other_name)),
        'paint_mtime': g(paint_name)['mtime'] if g(paint_name) else None,
        'spec_mtime': g(spec_name)['mtime'] if g(spec_name) else None,
    }
    mips = {}
    if rid:
        if g('car_spec_%s.mip' % rid):
            mips['spec'] = {'name': 'car_spec_%s.mip' % rid, 'mtime': g('car_spec_%s.mip' % rid)['mtime']}
        pm = ('car_num_%s.mip' if custom_number else 'car_%s.mip') % rid
        if g(pm):
            mips['paint'] = {'name': pm, 'mtime': g(pm)['mtime']}
    out['mips'] = mips

    pf = str(paint_file or '').strip().strip('"')
    pinfo = {'given': pf, 'exists': False, 'is_file': False, 'ext': '', 'size': None}
    if pf and (('\\' in pf) or ('/' in pf) or re.match(r'^[a-zA-Z]:', pf)) and not _is_unc(pf):
        m2 = re.match(r'^([a-zA-Z]):', pf)
        if not (m2 and _drive_is_remote(m2.group(1) + ':\\')):
            try:
                pinfo['exists'] = os.path.exists(pf)
                pinfo['is_file'] = os.path.isfile(pf)
                pinfo['ext'] = os.path.splitext(pf)[1].lower()
                if pinfo['is_file']:
                    pinfo['size'] = os.path.getsize(pf)
            except Exception:
                pass
    out['paint_file'] = pinfo
    return out


def probe(folder: str, iracing_id: str, custom_number: bool, paint_file: str) -> dict:
    """Time-boxed: a dead drive or a slow share must not hold the request (the worker thread may finish later on its own)."""
    fut = _POOL.submit(_probe, folder, iracing_id, custom_number, paint_file)
    try:
        return fut.result(timeout=4.0)
    except _Timeout:
        return {'ok': False, 'error': 'timeout', 'message': 'that folder did not answer in time (a slow or disconnected drive?)'}


def _loopback_host(host: str) -> bool:
    h = str(host or '').strip().lower()
    if h.startswith('['):
        h = h[1:h.find(']')] if ']' in h else h
    else:
        h = h.split(':')[0]
    return h in ('127.0.0.1', 'localhost', '::1')


_SHOW_NAME = re.compile(r'^car_(num_|spec_)?[0-9]{3,9}\.(tga|mip)$', re.I)
_JOB_ID = re.compile(r'^render_[0-9]{6,12}_[0-9]{0,9}_[0-9a-f]{6,32}$', re.I)


def show_files_target(folder: str, job_id: str, select: str, output_folder: str | None):
    """Where "Show my files" should open (2026-10-04, owner: a buyer kept looking in the wrong folder for his car_num/car_spec files).

    Returns (dir, file_or_None, error). Only ever opens a FOLDER window, optionally with one of the buyer's
    paint files highlighted (explorer /select); it never runs or opens a file. The folder is the one the render
    reported (output_dir / live_link path); with no iRacing folder set it is the render's own job folder."""
    d = str(folder or '').strip().strip('"')
    if d:
        if _is_unc(d):
            return None, None, 'network paths are not opened'
        m = re.match(r'^([a-zA-Z]):[\\/]', d)
        if m and _drive_is_remote(m.group(1) + ':\\'):
            return None, None, 'network drives are not opened'
        d = os.path.normpath(d)
        if os.path.isfile(d):
            d = os.path.dirname(d)
    elif job_id and output_folder:
        jid = str(job_id).strip()
        if not _JOB_ID.match(jid):
            return None, None, 'bad job id'
        d = os.path.join(output_folder, 'job_' + jid)
    if not d or not os.path.isdir(d):
        return None, None, 'folder not found'
    name = str(select or '').strip()
    pick = os.path.join(d, name) if name and _SHOW_NAME.match(name) and os.path.isfile(os.path.join(d, name)) else None
    return d, pick, None


def _open_in_explorer(d: str, pick: str | None):
    import subprocess
    import sys
    if sys.platform.startswith('win'):
        if pick:
            # explorer.exe parses its own command line: /select,"<file>" opens the folder with the file highlighted
            subprocess.Popen('explorer.exe /select,"%s"' % pick)
        else:
            os.startfile(d)  # a directory: opens an Explorer window, runs nothing
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', '-R', pick] if pick else ['open', d])
    else:
        subprocess.Popen(['xdg-open', d])


def register_support_routes(app, logger=None, output_folder=None):
    from flask import request, jsonify
    from server_routes.ai_copilot_routes import _origin_ok

    @app.route('/api/support/show-files', methods=['POST'])
    def support_show_files():
        """POST {folder?, job_id?, select?} -> opens Explorer on the rendered files. Loopback + local origin only."""
        if not _loopback_host(request.host) or not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        body = request.get_json(silent=True) or {}
        d, pick, err = show_files_target(body.get('folder', ''), body.get('job_id', ''), body.get('select', ''), output_folder)
        if err:
            return jsonify({'ok': False, 'error': err}), 200
        try:
            _open_in_explorer(d, pick)
        except Exception as e:
            return jsonify({'ok': False, 'error': 'could not open: %s' % str(e)[:120], 'path': d}), 200
        return jsonify({'ok': True, 'path': d, 'selected': os.path.basename(pick) if pick else None})

    @app.route('/api/support/folder-probe', methods=['POST'])
    def support_folder_probe():
        if not _loopback_host(request.host) or not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        body = request.get_json(silent=True) or {}
        try:
            res = probe(body.get('folder', ''), body.get('iracing_id', ''), bool(body.get('custom_number', True)), body.get('paint_file', ''))
            return jsonify(res)
        except Exception as e:
            try:
                if logger:
                    logger.warning('[SUPPORT] folder-probe failed: %s' % e)
            except Exception:
                pass
            return jsonify({'ok': False, 'error': 'failed', 'message': str(e)[:120]}), 200
