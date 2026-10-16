"""[CONNECT-CLAUDE 2026-10-10] One-click Claude setup from inside SPB (the AI panel's "Claude - Connect your Claude app" card).

Owner (orchestrator brief 2026-10-10): "most buyers will talk to SPB through Claude ... a fresh install must get Claude connected AND knowing
the app with as few steps as possible." The card (js/spb-ai-connect.js) shows four plain steps; these routes do the parts the page cannot:

  GET  /api/claude-connect/status              what this install ships + what can be SEEN on this PC (read-only; never guesses)
  POST /api/claude-connect/open-bundle         open the newest shipped .mcpb with its Windows handler (Claude Desktop asks the buyer to confirm)
  POST /api/claude-connect/reveal              {"what": "bundle" | "skill" | "code-skill"} -> Explorer opens with that file highlighted
  POST /api/claude-connect/install-code-skill  {"dry_run": bool} -> unpack the shipped skill zip into %USERPROFILE%\\.claude\\skills\\shokker-paint-booth\\
  GET  /api/claude-connect/desktop             [S22 2026-10-13 beta Claude setup] the setup card's ONE call: is Claude Desktop installed, is the Shokker connector in it, is it the version this SPB ships
                                               -> state no_desktop | not_added | outdated | disabled | connected | no_bundle (read-only: folders + the uninstall registry key)
  POST /api/claude-connect/open-download       [S22] open https://claude.ai/download (fixed address, no input) in the default browser

Files: the connector is the newest ``mcp/*.mcpb`` (found by discovery, no version is hard-coded; scripts/build_mcpb.py writes it). The skill is
``mcp/skill/shokker-paint-booth.zip`` (one folder ``shokker-paint-booth/`` with SKILL.md + references, built in _easy_claude_work/skill/).

Install rules (Claude Code skill): runs only on the buyer's click; writes ONLY the target folder above, plus, when a folder of that name
already exists and differs, moves it whole to ``%USERPROFILE%\\.claude\\backups\\shokker-paint-booth-skill-<stamp>\\`` first (the zip is unpacked
into a staging folder beside that backup and moved into place, so a half-written skill is never visible). Nothing is ever deleted.
Same files already there -> nothing is written ("up to date"). Zip members are checked (only ``shokker-paint-booth/...``, no ``..``, no
absolute paths, size and count caps).

Docs used for the steps (2026-10-10): support.claude.com/en/articles/12512180-use-skills-in-claude (Customize > Skills > "+" > Create skill >
Upload a skill; "Code execution and file creation" must be on, Settings > Capabilities) and code.claude.com/docs/en/skills (personal skills live
in ~/.claude/skills/<name>/SKILL.md and are picked up live; /reload-skills when the skills folder itself is new).

Env:
  SPB_CLAUDE_CONNECT_OFF=1        kill switch: every route answers 404 {"error": "off"} and the card falls back to the old steps
  SPB_CLAUDE_CONNECT_HOME=<dir>   TEST ONLY: use this folder as the user's home instead of %USERPROFILE% (lane tests never touch the real one)
  SPB_CLAUDE_CONNECT_NO_OPEN=1    TEST ONLY: open-bundle reports the file it would open instead of launching Claude Desktop's install dialog
  SPB_CLAUDE_CONNECT_DETECT_HOME=<dir>  TEST ONLY [S22]: /desktop looks for Claude Desktop only under <dir>/Local and <dir>/Roaming (and skips the registry); NO_OPEN also applies to open-download
"""
import glob
import hashlib
import json
import os
import re
import sys
import time
import zipfile

SKILL_NAME = 'shokker-paint-booth'
_MAX_FILES = 200
_MAX_BYTES = 8 * 1024 * 1024
_TRUE = ('1', 'true', 'yes', 'on')


def _env_on(k):
    return str(os.environ.get(k, '')).strip().lower() in _TRUE


def _off():
    return _env_on('SPB_CLAUDE_CONNECT_OFF')


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mcp_dir():
    return os.path.join(_root(), 'mcp')


def _home():
    return os.environ.get('SPB_CLAUDE_CONNECT_HOME') or os.environ.get('USERPROFILE') or os.path.expanduser('~')


def _paths():
    home = _home()
    cdir = os.path.join(home, '.claude')
    skills = os.path.join(cdir, 'skills')
    return {'home': home, 'claude': cdir, 'skills': skills, 'target': os.path.join(skills, SKILL_NAME), 'backups': os.path.join(cdir, 'backups')}


def _newest(paths):
    paths = [p for p in paths if os.path.isfile(p)]
    return max(paths, key=lambda p: os.path.getmtime(p)) if paths else None


def find_bundle():
    """Newest shipped Claude Desktop connector (.mcpb) - by discovery, so a rebuilt 1.4.x is picked up with no code change."""
    m = _mcp_dir()
    path = _newest(glob.glob(os.path.join(m, '*.mcpb')) + glob.glob(os.path.join(m, 'dist', '*.mcpb')))
    if not path:
        return {'found': False}
    out = {'found': True, 'path': path, 'file': os.path.basename(path), 'name': '', 'version': ''}
    try:
        with zipfile.ZipFile(path) as z:
            man = json.loads(z.read('manifest.json').decode('utf-8'))
        out['name'] = str(man.get('name') or '')[:80]
        out['version'] = str(man.get('version') or '')[:40]
    except Exception:
        pass
    return out


def _skill_members(z):
    """The zip's file members, validated. Raises ValueError on anything outside shokker-paint-booth/."""
    names, total = [], 0
    for i in z.infolist():
        n = i.filename.replace('\\', '/')
        if n.endswith('/'):
            continue
        parts = n.split('/')
        if (n.startswith('/') or re.match(r'^[A-Za-z]:', n) or parts[0] != SKILL_NAME or len(parts) < 2
                or any(p in ('', '.', '..') for p in parts)):
            raise ValueError('unexpected file in the skill zip: %s' % n[:120])
        total += i.file_size
        names.append((n, i))
    if not names or (SKILL_NAME + '/SKILL.md') not in [n for n, _ in names]:
        raise ValueError('the skill zip has no %s/SKILL.md' % SKILL_NAME)
    if len(names) > _MAX_FILES or total > _MAX_BYTES:
        raise ValueError('the skill zip is larger than expected')
    return names


def find_skill_zip():
    m = _mcp_dir()
    path = _newest(glob.glob(os.path.join(m, 'skill', '*.zip')))
    if not path:
        return {'found': False}
    out = {'found': True, 'path': path, 'file': os.path.basename(path), 'files': 0}
    try:
        with zipfile.ZipFile(path) as z:
            out['files'] = len(_skill_members(z))
    except Exception as e:
        out.update({'found': False, 'bad': str(e)[:160]})
    return out


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _installed_matches(zpath, target):
    """True when every file in the zip is already in target with the same bytes (and target has no other files)."""
    if not os.path.isdir(target):
        return False
    with zipfile.ZipFile(zpath) as z:
        want = {n[len(SKILL_NAME) + 1:]: _sha(z.read(i)) for n, i in _skill_members(z)}
    have = {}
    for dp, _dn, fns in os.walk(target):
        for f in fns:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, target).replace('\\', '/')
            if rel not in want:
                return False
            with open(full, 'rb') as fh:
                have[rel] = _sha(fh.read())
    return have == want


def code_skill_state():
    p = _paths()
    z = find_skill_zip()
    inst = os.path.isfile(os.path.join(p['target'], 'SKILL.md'))
    out = {'target': p['target'], 'installed': inst, 'upToDate': None}
    if inst and z.get('found'):
        try:
            out['upToDate'] = _installed_matches(z['path'], p['target'])
        except Exception:
            out['upToDate'] = None
    return out


def desktop_state(bundle_name):
    """What Claude Desktop shows on THIS PC (read-only): is it installed, and an installed extension whose id ends with the bundle name.
    [S22 2026-10-13 beta Claude setup] was %APPDATA%\\Claude only: now the same places the setup card looks (classic installer, Microsoft Store / MSIX package + its LocalCache\\Roaming copy, uninstall registry, %APPDATA%\\Claude), newest extension copy wins."""
    inst = claude_desktop_install()
    if not inst['installed']:
        return {'claudeDesktop': False, 'seen': False}
    out = {'claudeDesktop': True, 'seen': False}
    try:
        con = claude_connector_state(bundle_name, inst['dirs'])
        if con.get('seen'):
            out.update({'seen': True, 'version': con.get('version') or ''})
            if 'enabled' in con:
                out['enabled'] = con['enabled']
    except Exception:
        out['readError'] = True
    return out


# [S22 2026-10-13 beta Claude setup] ----- Claude Desktop detection for the setup card (read-only; never writes, never runs anything) -----
DOWNLOAD_URL = 'https://claude.ai/download'


def _detect_roots():
    """(local_appdata, roaming_appdata, use_registry). TEST ONLY: SPB_CLAUDE_CONNECT_DETECT_HOME roots both folders in a test dir and skips the registry."""
    fake = os.environ.get('SPB_CLAUDE_CONNECT_DETECT_HOME')
    if fake:
        return os.path.join(fake, 'Local'), os.path.join(fake, 'Roaming'), False
    return os.environ.get('LOCALAPPDATA') or '', os.environ.get('APPDATA') or '', True


def _registry_has_claude_desktop():
    """True when an Uninstall entry named Claude / Claude Desktop (publisher Anthropic or none) exists. Read-only registry access."""
    if not sys.platform.startswith('win'):
        return False
    try:
        import winreg
    except Exception:
        return False
    key = r'Software\Microsoft\Windows\CurrentVersion\Uninstall'
    for hive, view in ((winreg.HKEY_CURRENT_USER, 0), (winreg.HKEY_LOCAL_MACHINE, getattr(winreg, 'KEY_WOW64_64KEY', 0)), (winreg.HKEY_LOCAL_MACHINE, getattr(winreg, 'KEY_WOW64_32KEY', 0))):
        try:
            root = winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view)
        except OSError:
            continue
        with root:
            i = 0
            while i < 4000:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(root, sub) as sk:
                        dn = str(winreg.QueryValueEx(sk, 'DisplayName')[0]).strip().lower()
                        try:
                            pub = str(winreg.QueryValueEx(sk, 'Publisher')[0]).lower()
                        except OSError:
                            pub = ''
                except OSError:
                    continue
                if dn in ('claude', 'claude desktop') and (not pub or 'anthropic' in pub):
                    return True
    return False


def _store_package_roots():
    """Microsoft Store (MSIX) installs of Claude Desktop from the per-user package repository (read-only registry): [{'family': 'Claude_<publisherId>', 'root': <install location>}].
    The install location (C:\\Program Files\\WindowsApps\\Claude_<ver>_x64__<id>) cannot be listed by a normal app, but the registry names it and a plain stat on it works."""
    out = []
    if not sys.platform.startswith('win'):
        return out
    try:
        import winreg
        key = r'Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ) as root:
            i = 0
            while i < 4000:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                m = re.match(r'^Claude_[0-9.]+_[A-Za-z0-9]+__([a-z0-9]+)$', sub)
                if not m:
                    continue
                try:
                    with winreg.OpenKey(root, sub) as sk:
                        loc = str(winreg.QueryValueEx(sk, 'PackageRootFolder')[0])
                except OSError:
                    loc = ''
                out.append({'family': 'Claude_' + m.group(1), 'root': loc})
    except Exception:
        pass
    return out


def claude_desktop_install():
    """Is Claude Desktop on this PC? Looks in the usual places: %LOCALAPPDATA%\\AnthropicClaude (the classic installer), the Microsoft Store package folder,
    the uninstall registry key, and %APPDATA%\\Claude (its data folder; the weakest sign). Returns {installed, how:[...], dirs:[data folders]}."""
    local, roaming, use_reg = _detect_roots()
    how, dirs = [], []
    if local and os.path.isdir(os.path.join(local, 'AnthropicClaude')):
        how.append('localappdata')
    pk = os.path.join(local, 'Packages') if local else ''
    pkgs = glob.glob(os.path.join(pk, 'Claude_*')) if pk and os.path.isdir(pk) else []
    sroots = _store_package_roots() if use_reg else []          # [S22 2026-10-13] Store / MSIX: the package repository names the install location
    for r in sroots:          # a package family that has no Packages\<family> folder yet still counts, and its data folder is probed too
        fam = os.path.join(pk, r['family']) if pk else ''
        if fam and fam not in pkgs:
            pkgs.append(fam)
    if pkgs or sroots:
        how.append('store')
    if use_reg and _registry_has_claude_desktop():
        how.append('registry')
    if roaming and os.path.isdir(os.path.join(roaming, 'Claude')):
        how.append('appdata')
        dirs.append(os.path.join(roaming, 'Claude'))
    for p in pkgs:          # a Store install may keep its extensions in the package's own roaming copy (MSIX file virtualisation: %LOCALAPPDATA%\\Packages\\Claude_*\\LocalCache\\Roaming\\Claude)
        d = os.path.join(p, 'LocalCache', 'Roaming', 'Claude')
        if os.path.isdir(d) and d not in dirs:
            dirs.append(d)
    return {'installed': bool(how), 'how': how, 'dirs': dirs, 'store_root': (sroots[0]['root'] if sroots else '')}


def claude_connector_state(bundle_name, dirs):
    """The Shokker connector inside Claude Desktop: {seen, version, enabled}. Newest copy wins if two data folders both have one."""
    name = bundle_name or SKILL_NAME
    best = None
    for cdir in dirs:
        try:
            ext_root = os.path.join(cdir, 'Claude Extensions')
            for d in (os.listdir(ext_root) if os.path.isdir(ext_root) else []):
                if not d.endswith('.' + name):
                    continue
                mf = os.path.join(ext_root, d, 'manifest.json')
                if not os.path.isfile(mf):
                    continue
                with open(mf, encoding='utf-8') as fh:
                    man = json.load(fh)
                cur = {'seen': True, 'version': str(man.get('version') or '')[:40], '_t': os.path.getmtime(mf)}
                sf = os.path.join(cdir, 'Claude Extensions Settings', d + '.json')
                if os.path.isfile(sf):
                    with open(sf, encoding='utf-8') as fh:
                        st = json.load(fh)
                    if 'isEnabled' in st:
                        cur['enabled'] = bool(st.get('isEnabled'))
                if best is None or cur['_t'] > best['_t']:
                    best = cur
        except Exception:
            continue
    if best is None:
        return {'seen': False}
    best.pop('_t', None)
    return best


def setup_state():
    """Everything the setup card needs in one answer. state: no_bundle | no_desktop | not_added | outdated | disabled | connected."""
    b = find_bundle()
    inst = claude_desktop_install()
    con = claude_connector_state(b.get('name'), inst['dirs']) if inst['installed'] else {'seen': False}
    shipped = {'found': bool(b.get('found')), 'version': b.get('version') or '', 'file': b.get('file') or ''}
    if not b.get('found'):
        state = 'no_bundle'
    elif not inst['installed']:
        state = 'no_desktop'
    elif not con.get('seen'):
        state = 'not_added'
    elif shipped['version'] and con.get('version') != shipped['version']:
        state = 'outdated'
    elif con.get('enabled') is False:
        state = 'disabled'
    else:
        state = 'connected'
    return {'ok': True, 'state': state, 'desktop': {'installed': inst['installed'], 'how': inst['how'], 'storeRoot': inst.get('store_root') or ''}, 'connector': con, 'shipped': shipped}


def code_connector_state():
    """Claude Code's own config (~/.claude.json): is a Shokker MCP server listed? Read-only; None = Claude Code config not found."""
    f = os.path.join(_home(), '.claude.json')
    if not os.path.isfile(f):
        return {'claudeCode': os.path.isdir(_paths()['claude']), 'seen': None}
    try:
        if os.path.getsize(f) > 64 * 1024 * 1024:
            return {'claudeCode': True, 'seen': None}
        with open(f, encoding='utf-8') as fh:
            cfg = json.load(fh)
    except Exception:
        return {'claudeCode': True, 'seen': None}
    keys = list((cfg.get('mcpServers') or {}).keys())
    for proj in (cfg.get('projects') or {}).values():
        if isinstance(proj, dict):
            keys += list((proj.get('mcpServers') or {}).keys())
    return {'claudeCode': True, 'seen': any('shokker' in str(k).lower() for k in keys)}


def install_code_skill(dry_run=False):
    z = find_skill_zip()
    if not z.get('found'):
        return 404, {'ok': False, 'error': 'missing', 'message': 'The skill file is not in this install (mcp/skill/%s.zip).' % SKILL_NAME}
    p = _paths()
    target, stamp = p['target'], time.strftime('%Y%m%d-%H%M%S')
    exists = os.path.lexists(target)
    if exists and _installed_matches(z['path'], target):
        return 200, {'ok': True, 'status': 'up_to_date', 'dry_run': bool(dry_run), 'target': target, 'wrote': False}
    backup = os.path.join(p['backups'], '%s-skill-%s' % (SKILL_NAME, stamp)) if exists else None
    plan = {'ok': True, 'dry_run': bool(dry_run), 'target': target, 'backup': backup, 'files': z['files'],
            'newSkillsFolder': not os.path.isdir(p['skills'])}
    if dry_run:
        plan['status'] = 'would_install'
        return 200, plan
    stage = os.path.join(p['backups'], '.spb-skill-stage-%s' % stamp)
    os.makedirs(stage, exist_ok=False)
    with zipfile.ZipFile(z['path']) as zf:
        for n, info in _skill_members(zf):
            dst = os.path.normpath(os.path.join(stage, *n.split('/')))
            if not dst.startswith(os.path.normpath(stage) + os.sep):
                raise ValueError('unsafe path in skill zip')
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as fh:
                fh.write(zf.read(info))
    os.makedirs(p['skills'], exist_ok=True)
    if backup:
        os.replace(target, backup)
    try:
        os.replace(os.path.join(stage, SKILL_NAME), target)
    except Exception:
        if backup and not os.path.lexists(target):
            os.replace(backup, target)          # put the buyer's old folder back
        raise
    try:
        os.rmdir(stage)                         # empty now; never a recursive delete
    except OSError:
        pass
    plan.update({'status': 'installed', 'wrote': True})
    return 200, plan


def reveal(path):
    import subprocess
    if sys.platform.startswith('win'):
        subprocess.Popen('explorer.exe /select,"%s"' % os.path.normpath(path))   # opens the folder with the file highlighted; runs nothing
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', '-R', path])
    else:
        subprocess.Popen(['xdg-open', os.path.dirname(path)])


def register_claude_connect_routes(app, *, logger=None):
    from flask import jsonify, request
    from server_routes.ai_copilot_routes import _origin_ok

    def guard():
        if _off():
            return jsonify({'ok': False, 'error': 'off', 'message': 'Claude setup is switched off in this install.'}), 404
        if request.remote_addr not in ('127.0.0.1', '::1') or not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        return None

    def log(msg):
        try:
            if logger:
                logger.info('[CONNECT-CLAUDE] %s', msg)
        except Exception:
            pass

    @app.route('/api/claude-connect/status', methods=['GET'])
    def claude_connect_status():
        g = guard()
        if g:
            return g
        b = find_bundle()
        out = {'ok': True, 'bundle': b, 'skillZip': find_skill_zip(), 'codeSkill': code_skill_state(),
               'desktop': desktop_state(b.get('name'))}
        if request.args.get('deep') == '1':
            out['codeConnector'] = code_connector_state()
        return jsonify(out)

    @app.route('/api/claude-connect/desktop', methods=['GET'])          # [S22 2026-10-13 beta Claude setup]
    def claude_connect_desktop():
        g = guard()
        if g:
            return g
        try:
            return jsonify(setup_state())
        except Exception as e:
            return jsonify({'ok': False, 'error': 'detect_failed', 'message': 'Could not look for Claude Desktop: ' + str(e)[:120]}), 200

    @app.route('/api/claude-connect/open-download', methods=['POST'])          # [S22 2026-10-13 beta Claude setup]
    def claude_connect_open_download():
        g = guard()
        if g:
            return g
        if _env_on('SPB_CLAUDE_CONNECT_NO_OPEN'):
            return jsonify({'ok': True, 'opened': False, 'test': True, 'url': DOWNLOAD_URL})
        try:
            import webbrowser
            ok = webbrowser.open(DOWNLOAD_URL)          # a fixed address from this file, never from the request
        except Exception:
            ok = False
        if not ok:
            return jsonify({'ok': False, 'error': 'no_browser', 'url': DOWNLOAD_URL, 'message': 'Could not open your browser. Search for "Claude Desktop download" and install the free app.'}), 200
        log('opened the Claude Desktop download page')
        return jsonify({'ok': True, 'opened': True, 'url': DOWNLOAD_URL})

    @app.route('/api/claude-connect/open-bundle', methods=['POST'])
    def claude_connect_open_bundle():
        g = guard()
        if g:
            return g
        b = find_bundle()
        if not b.get('found'):
            return jsonify({'ok': False, 'error': 'missing', 'message': 'The Claude connector file is not in this install (mcp/*.mcpb).'}), 404
        if _env_on('SPB_CLAUDE_CONNECT_NO_OPEN'):
            return jsonify({'ok': True, 'opened': False, 'test': True, 'path': b['path'], 'version': b.get('version')})
        try:
            if hasattr(os, 'startfile'):
                os.startfile(b['path'])  # noqa: S606 (buyer's click, our own file; Claude Desktop asks them to confirm)
                log('opened %s' % b['file'])
                return jsonify({'ok': True, 'opened': True, 'path': b['path'], 'version': b.get('version')})
        except Exception as e:
            return jsonify({'ok': False, 'error': 'no_handler', 'path': b['path'],
                            'message': 'Windows has no program for .mcpb files yet: install Claude Desktop first (it is free; use the Get Claude Desktop button), then press the button again. (%s)' % str(e)[:80]}), 200
        return jsonify({'ok': False, 'error': 'unsupported', 'path': b['path'], 'message': 'Open this file yourself: ' + b['path']}), 200

    @app.route('/api/claude-connect/reveal', methods=['POST'])
    def claude_connect_reveal():
        g = guard()
        if g:
            return g
        what = str((request.get_json(silent=True) or {}).get('what') or '')
        if what == 'bundle':
            f = find_bundle()
        elif what == 'skill':
            f = find_skill_zip()
        elif what == 'code-skill':
            t = os.path.join(_paths()['target'], 'SKILL.md')
            f = {'found': os.path.isfile(t), 'path': t}
        else:
            return jsonify({'ok': False, 'error': 'bad_what'}), 400
        if not f.get('found'):
            return jsonify({'ok': False, 'error': 'missing', 'message': 'That file is not there.'}), 404
        try:
            reveal(f['path'])
        except Exception as e:
            return jsonify({'ok': False, 'error': 'reveal_failed', 'path': f['path'], 'message': 'Could not open Explorer: ' + str(e)[:80]}), 200
        log('revealed %s' % what)
        return jsonify({'ok': True, 'path': f['path']})

    @app.route('/api/claude-connect/install-code-skill', methods=['POST'])
    def claude_connect_install_code_skill():
        g = guard()
        if g:
            return g
        dry = bool((request.get_json(silent=True) or {}).get('dry_run'))
        try:
            code, body = install_code_skill(dry_run=dry)
        except Exception as e:
            return jsonify({'ok': False, 'error': 'install_failed', 'message': 'Could not install the skill: ' + str(e)[:160]}), 500
        if body.get('wrote'):
            log('installed Claude Code skill -> %s (backup %s)' % (body.get('target'), body.get('backup')))
        return jsonify(body), code
