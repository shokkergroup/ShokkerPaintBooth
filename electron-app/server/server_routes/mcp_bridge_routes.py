"""SPB MCP bridge — lets Claude Desktop / Claude Code (with the buyer's OWN subscription) drive Shokker Paint Booth  (SPB-AI 2026-09-30).

Why a bridge: the zone kit, car library, design library and live preview all run inside the app's page (renderer), not in this Flask process. The MCP server
(mcp/server/index.js, spawned by Claude Desktop over stdio) therefore cannot touch the paint directly. It posts a tool call here; the page, which long-polls this
module, executes the call with the SAME code the in-app copilot uses and posts the result back.

  MCP server  --POST /api/mcp/call (token)-->  this module  <--GET /api/mcp/poll (page, long-poll)--  page
                                                    ^------------POST /api/mcp/result (page)------------+

Safety:
  * OFF by default. The buyer turns it on in the AI panel ("Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth"). Turning it off fails every pending call.
  * /api/mcp/call needs a random pairing token (written to %APPDATA%/ShokkerPaintBooth/mcp/token.txt when the bridge is enabled; readable only by the same Windows user's
    processes) and a local request. A web page in the buyer's browser cannot call it (Origin / Sec-Fetch-Site check + token).
  * Only counts are logged. Prompts, results and images are never written to disk.
Routes: GET /api/mcp/status · POST /api/mcp/enable · GET /api/mcp/poll · POST /api/mcp/result · GET /api/mcp/ping · POST /api/mcp/call
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import threading
import time
import uuid
from collections import deque

_COND = threading.Condition()
_QUEUE = deque()           # calls waiting for the page: {id, tool, args}
_RESULTS = {}              # id -> {ok, result|error}
_PENDING = set()           # includes calls already delivered to the page
_STATE = {'enabled': False, 'last_poll': 0.0, 'calls': 0, 'last_tool': None, 'last_call': 0.0, 'loaded': False}
MAX_WAIT = 300.0
CONNECTED_WINDOW = 60.0    # the page counts as connected if it polled within this many seconds


def _dir() -> str:
    base = os.environ.get('SPB_MCP_DIR') or os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'ShokkerPaintBooth', 'mcp')
    os.makedirs(base, exist_ok=True)
    return base


def _settings_path() -> str:
    return os.path.join(_dir(), 'settings.json')


def token_path() -> str:
    return os.path.join(_dir(), 'token.txt')


def _atomic_write(path: str, text: str) -> None:
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


def _load() -> None:
    if _STATE['loaded']:
        return
    _STATE['loaded'] = True
    try:
        with open(_settings_path(), encoding='utf-8') as f:
            _STATE['enabled'] = bool(json.load(f).get('enabled'))
    except Exception:
        _STATE['enabled'] = False


def _token() -> str:
    try:
        with open(token_path(), encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ''


def _ensure_token() -> str:
    t = _token()
    if not t:
        t = secrets.token_hex(24)
        _atomic_write(token_path(), t)
    return t


def _mcp_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mcp')


def _connected() -> bool:
    # MCPSCEN 2026-10-05 (MCP run: a 60 s edit_layer was followed by get_zones -> 503 'not ready'): the page does not poll while it works on a
    # call, so a call still in progress (or a result just posted) also proves the page is alive.
    return bool(_PENDING) or (time.time() - _STATE['last_poll']) < CONNECTED_WINDOW


def _fail_all(reason: str) -> None:
    with _COND:
        _QUEUE.clear()
        for cid in _PENDING:
            _RESULTS[cid] = {'ok': False, 'error': reason}
        _COND.notify_all()


def register_mcp_bridge_routes(app, logger=None):
    from flask import request, jsonify
    from server_routes.ai_copilot_routes import _origin_ok

    def log(msg):
        try:
            if logger:
                logger.info('[MCP] ' + msg)
        except Exception:
            pass

    def page_guard():
        if request.remote_addr not in ('127.0.0.1', '::1') or not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        return None

    def token_guard():
        if request.remote_addr not in ('127.0.0.1', '::1') or not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin'}), 403
        _load()
        want = _token()
        got = request.headers.get('X-SPB-MCP-Token', '')
        if not want or not hmac.compare_digest(want, got):
            return jsonify({'ok': False, 'error': 'bad_token', 'message': 'Pairing token missing or wrong. Turn the bridge on in the Shokker AI panel, then restart your AI assistant (Claude or Codex).'}), 401
        return None

    def status_payload():
        _load()
        return {'ok': True, 'enabled': _STATE['enabled'], 'connected': _connected() and _STATE['enabled'], 'calls': _STATE['calls'], 'lastTool': _STATE['last_tool'],
                'lastCallAgo': (round(time.time() - _STATE['last_call']) if _STATE['last_call'] else None), 'tokenFile': token_path(), 'pending': len(_QUEUE), 'mcpDir': _mcp_dir(), 'bundle': os.path.exists(os.path.join(_mcp_dir(), 'shokker-paint-booth.mcpb'))}

    @app.route('/api/mcp/codex-setup', methods=['GET', 'POST'])
    def codex_setup():
        g = page_guard()
        if g:
            return g
        from server_routes.codex_setup import setup_payload, install_setup
        from urllib.parse import urlsplit
        try:
            payload = setup_payload(_mcp_dir(), urlsplit(request.host_url).port or 80)
        except ValueError:
            return jsonify({'ok': False, 'message': 'Could not determine the local SPB port.'}), 400
        if request.method == 'GET':
            return jsonify(payload)
        if (request.get_json(silent=True) or {}).get('confirmed') is not True:
            return jsonify({'ok': False, 'message': 'Confirm adding the shown SPB entry to Codex settings first.'}), 400
        try:
            return jsonify(install_setup(payload))
        except (OSError, ValueError) as exc:
            return jsonify({'ok': False, 'message': 'Codex settings were preserved. Setup could not finish: ' + str(exc)[:160]}), 409

    @app.route('/api/mcp/status', methods=['GET'])
    def mcp_status():
        g = page_guard()
        return g if g else jsonify(status_payload())

    @app.route('/api/mcp/enable', methods=['POST'])
    def mcp_enable():
        g = page_guard()
        if g:
            return g
        _load()
        on = bool((request.get_json(silent=True) or {}).get('enabled'))
        _STATE['enabled'] = on
        try:
            _atomic_write(_settings_path(), json.dumps({'enabled': on}))
        except Exception:
            pass
        if on:
            _ensure_token()
        else:
            _fail_all('The buyer switched the AI bridge off in Shokker Paint Booth.')
        log('bridge %s' % ('enabled' if on else 'disabled'))
        return jsonify(status_payload())

    @app.route('/api/mcp/poll', methods=['GET'])
    def mcp_poll():
        g = page_guard()
        if g:
            return g
        _load()
        try:
            wait = max(1.0, min(30.0, float(request.args.get('wait', '25'))))
        except Exception:
            wait = 25.0
        # MCPSCEN 2026-10-05 (a second Shokker page on the same server, here a stray browser tab, also polled: an AI's calls were split between two pages
        # with different zone stacks, so its edits landed on a car it was not looking at). ONE page owns the bridge: a page that just opened or that the
        # buyer switched the bridge on in claims it (claim=1, newest window wins); other pages get superseded and stop polling until the owner goes quiet.
        pid = str(request.args.get('page') or '')[:40]
        if pid:
            owner_alive = _STATE.get('owner') and (time.time() - _STATE.get('owner_poll', 0.0)) < CONNECTED_WINDOW
            if request.args.get('claim') == '1' or not owner_alive or _STATE.get('owner') == pid:
                _STATE['owner'] = pid
            else:
                return jsonify({'ok': True, 'enabled': _STATE['enabled'], 'superseded': True})
            _STATE['owner_poll'] = time.time()
        _STATE['last_poll'] = time.time()
        end = time.time() + wait
        with _COND:
            while not _QUEUE and time.time() < end and _STATE['enabled'] and (not pid or _STATE.get('owner') == pid):
                _COND.wait(timeout=min(2.0, max(0.05, end - time.time())))
                _STATE['last_poll'] = time.time()
                if pid and _STATE.get('owner') == pid:
                    _STATE['owner_poll'] = time.time()
            if pid and _STATE.get('owner') != pid:
                return jsonify({'ok': True, 'enabled': _STATE['enabled'], 'superseded': True})
            if _QUEUE and _STATE['enabled']:
                c = _QUEUE.popleft()
                return jsonify({'ok': True, 'call': c})
        return jsonify({'ok': True, 'enabled': _STATE['enabled']})

    @app.route('/api/mcp/result', methods=['POST'])
    def mcp_result():
        g = page_guard()
        if g:
            return g
        body = request.get_json(silent=True) or {}
        cid = str(body.get('id') or '')
        if not cid:
            return jsonify({'ok': False, 'error': 'no id'}), 400
        with _COND:
            if cid not in _PENDING or cid in _RESULTS:
                return jsonify({'ok': False, 'error': 'expired_call'}), 409
            _RESULTS[cid] = {'ok': bool(body.get('ok')), 'result': body.get('result'), 'error': body.get('error')}
            _STATE['last_poll'] = time.time()
            _COND.notify_all()
        return jsonify({'ok': True})

    @app.route('/api/mcp/open-bundle', methods=['POST'])
    def mcp_open_bundle():
        """Buyer pressed 'Install in Claude Desktop': open the .mcpb file with its Windows association (Claude Desktop shows its own install dialog and asks the buyer to confirm)."""
        g = page_guard()
        if g:
            return g
        bundle = os.path.join(_mcp_dir(), 'shokker-paint-booth.mcpb')
        if not os.path.exists(bundle):
            return jsonify({'ok': False, 'error': 'missing', 'message': 'The Claude extension file is not in this install (mcp/shokker-paint-booth.mcpb).'}), 404
        try:
            if hasattr(os, 'startfile'):
                os.startfile(bundle)  # noqa: S606 (user-initiated, our own file)
                return jsonify({'ok': True, 'opened': True, 'path': bundle})
        except Exception as e:  # no association (Claude Desktop not installed)
            return jsonify({'ok': False, 'error': 'no_handler', 'message': 'Windows has no program for .mcpb files: install Claude Desktop first (claude.ai/download), then press the button again. (%s)' % str(e)[:80], 'path': bundle}), 200
        return jsonify({'ok': False, 'error': 'unsupported', 'message': 'Open the file yourself: ' + bundle, 'path': bundle}), 200

    @app.route('/api/mcp/ping', methods=['GET'])
    def mcp_ping():
        g = token_guard()
        return g if g else jsonify(status_payload())

    @app.route('/api/mcp/call', methods=['POST'])
    def mcp_call():
        g = token_guard()
        if g:
            return g
        _load()
        if not _STATE['enabled']:
            return jsonify({'ok': False, 'error': 'disabled', 'message': 'The AI bridge is switched off in Shokker Paint Booth (AI panel -> settings).'}), 503
        if not _connected():
            return jsonify({'ok': False, 'error': 'app_not_ready', 'message': 'Shokker Paint Booth is not open in Pro mode with the AI panel loaded. Open the app and try again.'}), 503
        body = request.get_json(silent=True) or {}
        tool = str(body.get('tool') or '')[:60]
        if not tool:
            return jsonify({'ok': False, 'error': 'no tool'}), 400
        try:
            timeout = max(5.0, min(MAX_WAIT, float(body.get('timeout', 120))))
        except Exception:
            timeout = 120.0
        cid = uuid.uuid4().hex
        call = {'id': cid, 'tool': tool, 'args': body.get('args') if isinstance(body.get('args'), dict) else {}}
        with _COND:
            _PENDING.add(cid)
            _QUEUE.append(call)
            _COND.notify_all()
        _STATE['calls'] += 1
        _STATE['last_tool'] = tool
        _STATE['last_call'] = time.time()
        end = time.time() + timeout
        with _COND:
            while cid not in _RESULTS and time.time() < end:
                _COND.wait(timeout=min(2.0, max(0.05, end - time.time())))
            res = _RESULTS.pop(cid, None)
            _PENDING.discard(cid)
            if res is None:
                try:
                    _QUEUE.remove(call)
                except ValueError:
                    pass
        if res is None:
            return jsonify({'ok': False, 'error': 'timeout', 'message': 'Shokker Paint Booth did not answer in %d s (is the preview rendering, or is another AI answer running?).' % int(timeout)}), 504
        return jsonify(res)
