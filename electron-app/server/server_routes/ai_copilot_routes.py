"""SPB AI Copilot — OPTIONAL OpenRouter bridge  (SPB-AI 2026-09-30).

The buyer brings their own OpenRouter key. This module is the only place the key is ever held:

  * The browser NEVER sees the key. It calls /api/ai/chat on this local server; the server adds the key and forwards.
  * At rest the key is encrypted with Windows DPAPI (bound to the Windows user; ctypes, no dependency). On other
    platforms it is stored obfuscated-only and the status endpoint says so. Env var OPENROUTER_API_KEY overrides (dev/CI).
  * Only local origins may call these routes (a random web page cannot burn a buyer's credits through 127.0.0.1).
  * A local daily soft cap (default $2/day) stops runaway loops before OpenRouter's own key limit does.
  * Nothing is logged except counts and cost. Prompts / replies / the key are never written to any log.

Routes: GET /api/ai/status · POST /api/ai/settings · GET /api/ai/models · GET /api/ai/credits · POST /api/ai/chat · POST /api/ai/test
The chat route is a thin, validated pass-through of OpenAI-style chat/completions (messages, tools, tool_choice, max_tokens,
temperature); the tool LOOP runs in the page, where the paint state and the Easy API live.
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request

OPENROUTER_BASE = os.environ.get('SPB_OPENROUTER_BASE', 'https://openrouter.ai/api/v1').rstrip('/')
DEFAULT_MODEL = 'deepseek/deepseek-v4.1-flash'
# COPILOT-FIX 2026-10-04 (owner law "ONE copilot model = the gear's model, ever"): the old separate vision model
# (deepseek-v4-flash-vision-exp, falling back to qwen3.7-flash) and any client-chosen model are gone. Every chat call runs on the
# gear's MODEL; a picture call on a model that cannot read pictures is refused (error 'no_vision', no cost) and the app's measured
# checks decide alone. The only other model ever used is settings.escalateModel, an explicit opt-in saved through /api/ai/settings
# and reported by /api/ai/status (empty by default). The owner's test: claude-haiku-4.5 repaired + qwen judged a DeepSeek turn.
MODES = ('off', 'auto', 'always')
MAX_BODY_CHARS = 1_400_000                                 # room for one reference picture (<=1400px JPEG, 2026-10-02) or a ~512px look & refine JPEG
MAX_TOKENS_CAP = 4096
_LOCK = threading.Lock()
_MODELS_CACHE = {'t': 0.0, 'data': None}
_RECENT = []
# HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- FINAL 5a owner MANDATE (binding): "anything I type into the
# AI helper boxes gets logged somewhere at least temporarily where you can pull the chat logs and SEE what happened". One JSON line per
# typed turn (offline route, builder, online chat, chip clicks: posted by js/spb-offline-builder.js to /api/ai/turn-log) and per online
# model call (/api/ai/chat below), LOCAL ONLY: output/ai_logs/copilot_turns.jsonl, rotated at 5 MB, the last 4 files kept.
# Read it with: python scripts/ai_logs_tail.py [-n 20]
_TURNLOG_MAX = 5 * 1024 * 1024
_TURNLOG_KEEP = 4
_TURNLOG_LOCK = threading.Lock()


def _turnlog_dir() -> str:
    d = os.environ.get('SPB_AI_LOG_DIR') or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output', 'ai_logs')
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:                                      # a read-only install folder: keep the log beside the AI settings instead
        d = os.path.join(_dir(), 'ai_logs')
        os.makedirs(d, exist_ok=True)
    return d


def _turnlog(rec: dict) -> None:
    try:
        rec = dict(rec or {})
        rec.setdefault('ts', _dt.datetime.now().isoformat(timespec='seconds'))
        # orchestrator 2026-10-05: the test server (59879) and the live one (59876) share output/ai_logs -> every record carries the port it came in on
        port = None
        try:
            from flask import request as _rq, has_request_context as _hrc
            if _hrc():
                port = int(str(_rq.host or '').rsplit(':', 1)[-1])
        except Exception:
            port = None
        if port is None:
            try:
                port = int(os.environ.get('SHOKKER_PORT') or 0) or None
            except Exception:
                port = None
        rec['port'] = port
        rec.setdefault('src', 'model' if rec.get('kind') in ('chat', 'chat_fail') else 'page')
        line = json.dumps(rec, ensure_ascii=False, default=str)
        if len(line) > 200_000:
            line = json.dumps({'ts': rec.get('ts'), 'kind': rec.get('kind'), 'text': str(rec.get('text') or '')[:2000], 'truncated': len(line)}, ensure_ascii=False)
        with _TURNLOG_LOCK:
            p = os.path.join(_turnlog_dir(), 'copilot_turns.jsonl')
            if os.path.exists(p) and os.path.getsize(p) > _TURNLOG_MAX:
                for i in range(_TURNLOG_KEEP - 1, 0, -1):
                    a, b = '%s.%d' % (p, i), '%s.%d' % (p, i + 1)
                    if os.path.exists(a):
                        os.replace(a, b)
                os.replace(p, p + '.1')
            with open(p, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
    except Exception:
        pass


def _msg_text(m) -> str:
    c = (m or {}).get('content') if isinstance(m, dict) else None
    if isinstance(c, list):
        c = ' '.join(str(x.get('text') or '') for x in c if isinstance(x, dict) and x.get('type') == 'text')
    return str(c or '')


# ----------------------------------------------------------------------------- storage
def _dir() -> str:
    base = os.environ.get('SPB_AI_DIR') or os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'ShokkerPaintBooth', 'ai')
    os.makedirs(base, exist_ok=True)
    return base


def _path(name: str) -> str:
    return os.path.join(_dir(), name)


def _atomic_write(path: str, text: str) -> None:
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


# --- Windows DPAPI (ctypes). CryptProtectData binds the blob to the current Windows user account.
def _dpapi(data: bytes, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    inb = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    outb = BLOB()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    ok = fn(ctypes.byref(inb), None, None, None, None, 0, ctypes.byref(outb))
    if not ok:
        raise OSError('DPAPI failed')
    try:
        return ctypes.string_at(outb.pbData, outb.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(outb.pbData)


def _seal(secret: str) -> dict:
    raw = secret.encode('utf-8')
    if sys.platform == 'win32':
        try:
            return {'enc': 'dpapi', 'blob': base64.b64encode(_dpapi(raw, True)).decode('ascii')}
        except Exception:
            pass
    return {'enc': 'plain-b64', 'blob': base64.b64encode(raw).decode('ascii')}


def _unseal(rec: dict) -> str:
    try:
        raw = base64.b64decode(rec.get('blob', ''))
        if rec.get('enc') == 'dpapi':
            raw = _dpapi(raw, False)
        return raw.decode('utf-8')
    except Exception:
        return ''


def _load_settings() -> dict:
    try:
        with open(_path('settings.json'), 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save_settings(d: dict) -> None:
    _atomic_write(_path('settings.json'), json.dumps(d, indent=1))


def _get_key() -> str:
    try:
        if _is_local():
            return 'local'
    except Exception:
        pass
    env = (os.environ.get('OPENROUTER_API_KEY') or '').strip()
    if env:
        return env
    rec = _load_settings().get('key')
    return _unseal(rec).strip() if isinstance(rec, dict) else ''


def _mask(key: str) -> str:
    if not key:
        return ''
    return key[:8] + '…' + key[-4:] if len(key) > 14 else '…'


# ----------------------------------------------------------------------------- ledger (cost per local day)
def _today() -> str:
    return _dt.date.today().isoformat()


def _ledger() -> dict:
    try:
        with open(_path('ledger.json'), 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ledger_add(cost: float, ptok: int, ctok: int) -> dict:
    with _LOCK:
        led = _ledger()
        day = led.get(_today(), {'cost': 0.0, 'prompt': 0, 'completion': 0, 'calls': 0})
        day['cost'] = round(float(day.get('cost', 0)) + float(cost or 0), 6)
        day['prompt'] = int(day.get('prompt', 0)) + int(ptok or 0)
        day['completion'] = int(day.get('completion', 0)) + int(ctok or 0)
        day['calls'] = int(day.get('calls', 0)) + 1
        led[_today()] = day
        for k in sorted(led.keys())[:-30]:            # keep 30 days
            led.pop(k, None)
        _atomic_write(_path('ledger.json'), json.dumps(led))
        return day


def _today_stats() -> dict:
    d = _ledger().get(_today(), {})
    return {'cost': round(float(d.get('cost', 0)), 6), 'prompt': int(d.get('prompt', 0)), 'completion': int(d.get('completion', 0)), 'calls': int(d.get('calls', 0))}


# ----------------------------------------------------------------------------- provider: OpenRouter (default) or a model running on THIS PC (Ollama / LM Studio / llama.cpp: any OpenAI-compatible server on loopback)
LOCAL_BASE_RE = re.compile(r'^http://(127\.0\.0\.1|localhost|\[::1\]):\d{2,5}(/[\w./-]*)?$', re.I)
DEFAULT_LOCAL_BASE = 'http://127.0.0.1:11434/v1'      # Ollama's OpenAI-compatible endpoint


def _is_local(s: dict | None = None) -> bool:
    s = s if s is not None else _load_settings()
    return s.get('provider') == 'local' and bool(LOCAL_BASE_RE.match(str(s.get('localBase') or DEFAULT_LOCAL_BASE)))


def _active_base() -> str:
    s = _load_settings()
    return (str(s.get('localBase') or DEFAULT_LOCAL_BASE).rstrip('/') if _is_local(s) else OPENROUTER_BASE)


# ----------------------------------------------------------------------------- upstream
def _http(method: str, path: str, key: str, body: dict | None = None, timeout: float = 90.0):
    local = _is_local()
    headers = ({'Authorization': 'Bearer local', 'Content-Type': 'application/json'} if local else
               {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json', 'HTTP-Referer': 'https://shokkerpaintbooth.com', 'X-Title': 'Shokker Paint Booth'})
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(_active_base() + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode('utf-8', 'replace') or '{}')
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'error': {'message': raw[:300]}}
    except Exception as e:                             # timeout, DNS, TLS ...
        return 0, {'error': {'message': str(e)[:200]}}


def _err(status: int, payload) -> dict:
    msg = ''
    try:
        msg = (payload.get('error') or {}).get('message') or ''
    except Exception:
        pass
    if status in (401, 403):
        code, human = 'bad_key', 'OpenRouter did not accept the key. Check it in AI settings.'
    elif status == 402:
        code, human = 'no_credit', 'Your OpenRouter credit (or this key’s spending limit) has run out.'
    elif status == 429:
        code, human = 'rate_limited', 'The model is busy or rate-limited right now. Try again in a moment, or pick another model.'
    elif status == 0 and _is_local():
        code, human = 'offline', 'Could not reach the model on this PC. Is Ollama (or LM Studio) running, and is the model name right?'
    elif status == 0:
        code, human = 'offline', 'Could not reach OpenRouter. Check your internet connection.'
    else:
        code, human = 'upstream', 'The model provider returned an error.'
    return {'ok': False, 'error': code, 'message': human, 'detail': msg[:200], 'status': status}


# ----------------------------------------------------------------------------- helpers
def _origin_ok(req) -> bool:
    """Only this app (or a local tool) may call the AI routes; a remote page in the buyer's browser may not."""
    origin = req.headers.get('Origin')
    if origin:
        m = re.match(r'^(?:https?|app|file)://(\[::1\]|localhost|127\.0\.0\.1)(?::\d+)?$', origin.strip(), re.I)
        if not m:
            return False
    sfs = (req.headers.get('Sec-Fetch-Site') or '').lower()
    return sfs in ('', 'same-origin', 'same-site', 'none') or bool(origin)


def _model_row(x: dict) -> dict:
    p = x.get('pricing') or {}
    try:
        pin, pout = float(p.get('prompt', 0)) * 1e6, float(p.get('completion', 0)) * 1e6
    except Exception:
        pin = pout = 0.0
    sp = x.get('supported_parameters') or []
    arch = x.get('architecture') or {}
    return {'id': x.get('id'), 'name': x.get('name') or x.get('id'), 'in': round(pin, 4), 'out': round(pout, 4),
            'ctx': x.get('context_length'), 'tools': 'tools' in sp, 'vision': 'image' in (arch.get('input_modalities') or []),
            'free': pin == 0 and pout == 0}


def _cached_row(model: str):
    for r in (_MODELS_CACHE.get('data') or []):
        if r.get('id') == model:
            return r
    return None


def _model_sees(key, model: str, fetch: bool = True):
    """True / False = the OpenRouter catalogue says whether `model` accepts images; None = unknown (no key, offline, not listed)."""
    if not model:
        return None
    if fetch and key and (not _MODELS_CACHE['data'] or time.time() - _MODELS_CACHE['t'] > 3600):
        try:
            st, d = _http('GET', '/models', key, None, 20)
            if st == 200 and isinstance(d, dict):
                _MODELS_CACHE.update({'t': time.time(), 'data': [_model_row(x) for x in (d.get('data') or []) if x.get('id')]})
        except Exception:
            pass
    r = _cached_row(model)
    return None if r is None else bool(r.get('vision'))


def _clean_messages(msgs):
    out = []
    for m in msgs[:80]:
        if not isinstance(m, dict) or m.get('role') not in ('system', 'user', 'assistant', 'tool'):
            continue
        keep = {k: m[k] for k in ('role', 'content', 'tool_calls', 'tool_call_id', 'name') if k in m}
        if isinstance(keep.get('content'), list):                       # multimodal parts: keep text + data-URL images only
            parts = []
            for p in keep['content'][:6]:
                if isinstance(p, dict) and p.get('type') == 'text':
                    parts.append({'type': 'text', 'text': str(p.get('text', ''))[:20000]})
                elif isinstance(p, dict) and p.get('type') == 'image_url' and isinstance((p.get('image_url') or {}).get('url'), str) and p['image_url']['url'].startswith('data:image/'):
                    parts.append({'type': 'image_url', 'image_url': {'url': p['image_url']['url']}})
            keep['content'] = parts
        out.append(keep)
    return out


# FIRSTTEST 2026-10-04 (owner's first test: the reply ended with raw "<｜DSML｜calls> <｜DSML｜invoke name="describe_paint"> ..." markup): DeepSeek sometimes writes its tool
# calls as TEXT in its own DSML markup instead of real tool_calls (or leaves a residue such as `="zone" string="false">1`). Well-formed invoke blocks for tools the request
# offered become real tool_calls (the client runs them like any other call); everything else of that markup is stripped. The buyer never sees it.
_BAR = '[|\uff5c]'
_DSML_INVOKE = re.compile(r'<\s*(?:' + _BAR + r'\s*)+DSML\s*(?:' + _BAR + r'\s*)+invoke\s+name\s*=\s*"([^"]{1,64})"\s*>(.*?)<\s*/\s*(?:' + _BAR + r'\s*)+DSML\s*(?:' + _BAR + r'\s*)+invoke\s*>', re.S | re.I)
_DSML_PARAM = re.compile(r'<\s*(?:' + _BAR + r'\s*)+DSML\s*(?:' + _BAR + r'\s*)+parameter\s+name\s*=\s*"([^"]{1,64})"(?:\s+string\s*=\s*"(true|false)")?\s*>(.*?)<\s*/\s*(?:' + _BAR + r'\s*)+DSML\s*(?:' + _BAR + r'\s*)+parameter\s*>', re.S | re.I)
_DSML_BLOCK = re.compile(r'<\s*(?:' + _BAR + r'\s*)+DSML\s*(?:' + _BAR + r'\s*)+(?:function_)?calls\s*>.*?(?:<\s*/\s*(?:' + _BAR + r'\s*)+DSML\s*(?:' + _BAR + r'\s*)+(?:function_)?calls\s*>|$)', re.S | re.I)
_DSML_TAG = re.compile(r'<\s*/?\s*(?:' + _BAR + r'\s*)+DSML\s*(?:' + _BAR + r'\s*)+[^>]*>', re.I)
_DSML_RESIDUE = re.compile(r'(?:^|[ \t]*)(?:="?)?[A-Za-z_][\w.-]{0,40}"?\s+string="(?:true|false)"\s*>[^<\n]{0,400}(?:<\s*/[^>\n]{0,60}>)?')


def _dsml_split(content, tool_names):
    """-> (tool_calls or None, cleaned content). tool_calls only for invoke blocks of offered tools whose parameters all parse."""
    if not isinstance(content, str) or not re.search(r'DSML|string="(?:true|false)"', content):
        return None, content
    calls, ok = [], True
    for n, (name, body) in enumerate(_DSML_INVOKE.findall(content)):
        if tool_names and name not in tool_names:
            ok = False
            continue
        args = {}
        for pname, is_str, val in _DSML_PARAM.findall(body):
            if is_str.lower() == 'false':
                try:
                    args[pname] = json.loads(val.strip())
                except Exception:
                    ok = False
                    args[pname] = val.strip()
            else:
                args[pname] = val
        rest = _DSML_PARAM.sub('', body).strip()
        if rest and _DSML_TAG.sub('', rest).strip():
            ok = False
        calls.append({'id': 'dsml_%d_%d' % (int(time.time() * 1000) % 100000000, n), 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}})
    cleaned = _DSML_BLOCK.sub(' ', content)
    cleaned = _DSML_INVOKE.sub(' ', cleaned)
    cleaned = _DSML_TAG.sub(' ', cleaned)
    cleaned = _DSML_RESIDUE.sub(' ', cleaned)
    cleaned = re.sub(r'[ \t]+\n', '\n', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned).strip()
    return (calls if (calls and ok) else None), cleaned


def register_ai_copilot_routes(app, logger=None):
    from flask import request, jsonify

    def log(msg):
        try:
            if logger:
                logger.info('[AI] ' + msg)
        except Exception:
            pass

    # ONLINE_GROUNDING 2026-10-04: the SPB Encyclopedia search (/api/encyclopedia/search) that the online model and MCP share with
    # the offline helper (same BM25F port, parity-checked). Registered here so server.py / server_v5.py need no edit.
    try:
        from server_routes.encyclopedia_routes import register_encyclopedia_routes
        register_encyclopedia_routes(app, logger)
    except Exception as e:  # pragma: no cover - the copilot must still start
        log('encyclopedia search not registered: %s' % e)

    def guard():
        if not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin', 'message': 'Blocked: AI routes are for the Shokker app only.'}), 403
        return None

    def status_payload():
        s = _load_settings()
        key = _get_key()
        rec = s.get('key') if isinstance(s.get('key'), dict) else {}
        loc = _is_local(s)
        return {'ok': True, 'provider': 'local' if loc else 'openrouter', 'localBase': str(s.get('localBase') or DEFAULT_LOCAL_BASE), 'localModel': str(s.get('localModel') or ''), 'configured': bool(key) and (not loc or bool(s.get('localModel'))), 'keyMasked': _mask(key), 'keyFromEnv': bool(os.environ.get('OPENROUTER_API_KEY')),
                'storage': ('env' if os.environ.get('OPENROUTER_API_KEY') else rec.get('enc', '')),
                'model': s.get('model') or DEFAULT_MODEL, 'visionModel': s.get('model') or DEFAULT_MODEL,          # COPILOT-FIX: pictures go to the gear model too (kept for older panels that read it)
                'modelSeesPictures': None if loc else _model_sees(None, s.get('model') or DEFAULT_MODEL, fetch=False), 'escalateModel': str(s.get('escalateModel') or ''), 'mode': s.get('mode') if s.get('mode') in MODES else 'auto',
                'dailyCap': float(s.get('dailyCap', 2.0)), 'today': _today_stats(), 'vision': bool(s.get('vision', False))}

    @app.route('/api/ai/status', methods=['GET'])
    def ai_status():
        g = guard()
        return g if g else jsonify(status_payload())

    @app.route('/api/ai/settings', methods=['POST'])
    def ai_settings():
        g = guard()
        if g:
            return g
        body = request.get_json(silent=True) or {}
        s = _load_settings()
        if 'key' in body:
            k = str(body.get('key') or '').strip()
            if not k:
                s.pop('key', None)
            elif not re.match(r'^sk-or-[A-Za-z0-9_\-]{16,200}$', k):
                return jsonify({'ok': False, 'error': 'bad_format', 'message': 'That does not look like an OpenRouter key (it starts with sk-or-).'}), 400
            else:
                s['key'] = _seal(k)
        if 'provider' in body:
            if body['provider'] not in ('openrouter', 'local'):
                return jsonify({'ok': False, 'error': 'bad_provider'}), 400
            s['provider'] = body['provider']
        if 'localBase' in body:
            lb = str(body.get('localBase') or DEFAULT_LOCAL_BASE).strip().rstrip('/')
            if not LOCAL_BASE_RE.match(lb):
                return jsonify({'ok': False, 'error': 'bad_base', 'message': 'The local server address must look like http://127.0.0.1:11434/v1 (this computer only).'}), 400
            s['localBase'] = lb
        if 'localModel' in body:
            lm = str(body.get('localModel') or '').strip()
            if lm and not re.match(r'^[\w.\-~:/]{2,120}$', lm):
                return jsonify({'ok': False, 'error': 'bad_model', 'message': 'Unknown model name.'}), 400
            s['localModel'] = lm
        if 'model' in body:
            mid = str(body.get('model') or '').strip()
            if not re.match(r'^[\w.\-~:/]{3,120}$', mid):
                return jsonify({'ok': False, 'error': 'bad_model', 'message': 'Unknown model id.'}), 400
            s['model'] = mid
        if 'mode' in body:
            if body['mode'] not in MODES:
                return jsonify({'ok': False, 'error': 'bad_mode'}), 400
            s['mode'] = body['mode']
        if 'dailyCap' in body:
            try:
                s['dailyCap'] = max(0.05, min(500.0, float(body['dailyCap'])))
            except Exception:
                return jsonify({'ok': False, 'error': 'bad_cap'}), 400
        if 'vision' in body:
            s['vision'] = bool(body['vision'])
        if 'visionModel' in body:
            vm = str(body.get('visionModel') or '').strip()
            if not re.match(r'^[\w.\-~:/]{3,120}$', vm):
                return jsonify({'ok': False, 'error': 'bad_model', 'message': 'Unknown model id.'}), 400
            s['visionModel'] = vm          # COPILOT-FIX: stored for older panels only; no chat call uses it any more
        if 'escalateModel' in body:          # COPILOT-FIX: the ONE explicit opt-in to a second (repair) model; '' / 'off' = none (the default)
            em = str(body.get('escalateModel') or '').strip()
            if em in ('', 'off'):
                s.pop('escalateModel', None)
            elif not re.match(r'^[\w.\-~:/]{3,120}$', em):
                return jsonify({'ok': False, 'error': 'bad_model', 'message': 'Unknown model id.'}), 400
            else:
                s['escalateModel'] = em
        _save_settings(s)
        log('settings saved (key ' + ('set' if 'key' in s else 'absent') + ', model ' + str(s.get('model')) + ')')
        return jsonify(status_payload())

    @app.route('/api/ai/models', methods=['GET'])
    def ai_models():
        g = guard()
        if g:
            return g
        key = _get_key()
        now = time.time()
        if _is_local():
            st, d = _http('GET', '/models', 'local', None, 8)
            if st != 200:
                return jsonify(_err(st, d)), 502
            return jsonify({'ok': True, 'models': [{'id': x.get('id'), 'name': x.get('id'), 'in': 0, 'out': 0, 'ctx': None, 'tools': True, 'vision': False, 'free': True} for x in (d.get('data') or []) if x.get('id')]})
        if request.args.get('refresh') == '1' or not _MODELS_CACHE['data'] or now - _MODELS_CACHE['t'] > 900:
            if not key:
                return jsonify({'ok': False, 'error': 'no_key', 'message': 'Add your OpenRouter key first.'}), 400
            st, d = _http('GET', '/models', key, None, 30)
            if st != 200:
                return jsonify(_err(st, d)), 502
            rows = [_model_row(x) for x in (d.get('data') or []) if x.get('id')]
            _MODELS_CACHE.update({'t': now, 'data': rows})
        rows = [r for r in _MODELS_CACHE['data'] if r['tools']]
        rows.sort(key=lambda r: (r['in'] + r['out'], r['id']))
        return jsonify({'ok': True, 'models': rows})

    @app.route('/api/ai/credits', methods=['GET'])
    def ai_credits():
        g = guard()
        if g:
            return g
        key = _get_key()
        if not key:
            return jsonify({'ok': False, 'error': 'no_key', 'message': 'Add your OpenRouter key first.'}), 400
        st, d = _http('GET', '/auth/key', key, None, 20)
        if st != 200:
            return jsonify(_err(st, d)), 502
        dd = d.get('data', d)
        return jsonify({'ok': True, 'limit': dd.get('limit'), 'remaining': dd.get('limit_remaining'), 'usage': dd.get('usage'), 'usageDaily': dd.get('usage_daily'), 'free': dd.get('is_free_tier')})

    @app.route('/api/ai/chat', methods=['POST'])
    def ai_chat():
        g = guard()
        if g:
            return g
        key = _get_key()
        if not key:
            return jsonify({'ok': False, 'error': 'no_key', 'message': 'AI is not set up yet — add your OpenRouter key in AI settings.'}), 400
        raw = request.get_data(as_text=True) or ''
        if len(raw) > MAX_BODY_CHARS:
            return jsonify({'ok': False, 'error': 'too_big', 'message': 'That request is too large.'}), 413
        try:
            body = json.loads(raw)
        except Exception:
            return jsonify({'ok': False, 'error': 'bad_json'}), 400
        now_t = time.time()                                   # runaway-loop brake: 100 chat requests per rolling minute (a rich Pro turn = up to ~25 calls: research, vision, repair, options)
        with _LOCK:
            _RECENT[:] = [t for t in _RECENT if now_t - t < 60]
            if len(_RECENT) >= 100:
                return jsonify({'ok': False, 'error': 'rate_limited', 'message': 'Slow down a little — too many AI requests in a minute.'}), 429
            _RECENT.append(now_t)
        s = _load_settings()
        cap = float(s.get('dailyCap', 2.0))
        if (not _is_local(s)) and _today_stats()['cost'] >= cap:
            return jsonify({'ok': False, 'error': 'daily_cap', 'message': 'Today’s AI spending cap ($%.2f) is reached. Raise it in AI settings to continue.' % cap}), 429
        loc = _is_local(s)
        # COPILOT-FIX 2026-10-04: ONE model = the gear's. A client-requested model is honoured only when it IS the gear model or the
        # explicit escalateModel opt-in; anything else (an old page asking for claude-haiku / qwen) is ignored and logged.
        gear = str(s.get('model') or DEFAULT_MODEL)
        asked = str(body.get('model') or '').strip()
        model = str(s.get('localModel') or '') if loc else gear
        if asked and not loc and asked != gear:
            if asked == str(s.get('escalateModel') or ''):
                model = asked
            else:
                log('chat ignored requested model=%s (gear model only: %s)' % (asked[:80], gear))
        if not re.match(r'^[\w.\-~:/]{3,120}$', model):
            return jsonify({'ok': False, 'error': 'bad_model'}), 400
        if body.get('vision') and not loc and _model_sees(key, model) is False:
            log('chat model=%s skipped: cannot read pictures (vision call refused, no cost)' % model)
            return jsonify({'ok': False, 'error': 'no_vision', 'model': model, 'message': 'The Copilot model (%s) cannot read pictures, so the picture check was skipped.' % model})
        msgs = _clean_messages(body.get('messages') or [])
        if not msgs:
            return jsonify({'ok': False, 'error': 'no_messages'}), 400
        up = {'model': model, 'messages': msgs, **({} if loc else {'usage': {'include': True}}),
              'max_tokens': int(max(16, min(MAX_TOKENS_CAP, int(body.get('max_tokens') or 900)))),
              'temperature': float(max(0.0, min(1.5, float(body.get('temperature', 0.3)))))}
        rz = body.get('reasoning')                        # OpenRouter's unified reasoning switch (cheap tool calls don't need long thinking)
        if isinstance(rz, dict) and not loc:
            up['reasoning'] = {k: rz[k] for k in ('effort', 'max_tokens', 'enabled', 'exclude') if k in rz}
        tools = body.get('tools')
        if isinstance(tools, list) and tools:
            up['tools'] = tools[:24]
            up['tool_choice'] = body.get('tool_choice') or 'auto'
            if not loc:
                up['provider'] = {'require_parameters': True}
        t0 = time.time()
        st, d = _http('POST', '/chat/completions', key, up, 50)
        if st == 0:                                                     # timeout / dropped connection: one automatic retry (a hung request used to cost ~100 s and then fail)
            time.sleep(1.0); st, d = _http('POST', '/chat/completions', key, up, 60)
        if st in (400, 404) and 'reasoning' in up:                      # some models/providers cannot switch reasoning off: retry plain, once
            up.pop('reasoning', None)
            st, d = _http('POST', '/chat/completions', key, up, 100)
        # 2026-10-02: with tools we ask OpenRouter for `require_parameters` (never silently route to a provider that ignores the tools). Frontier models (GPT-5.x, Fable 5.1) accept no `temperature`,
        # so NO endpoint was left: "No endpoints found that can handle the requested parameters" (404) and the in-app copilot could not use them. Drop the optional sampling parameters one step at a time.
        if st in (400, 404) and not loc and 'tools' in up and 'No endpoints found' in json.dumps(d if isinstance(d, (dict, list)) else str(d))[:900]:
            for dropped in (('temperature',), ('temperature', 'reasoning'), ('temperature', 'reasoning', 'tool_choice')):
                up2 = {k: v for k, v in up.items() if k not in dropped}
                st, d = _http('POST', '/chat/completions', key, up2, 100)
                if st == 200:
                    up = up2; log('chat model=%s needed the request without %s' % (model, '+'.join(dropped))); break
        if st != 200 or not isinstance(d, dict) or not d.get('choices'):
            log('chat model=%s failed status=%s %.1fs' % (model, st, time.time() - t0))
            _turnlog({'kind': 'chat_fail', 'model': model, 'status': st, 'user': next((_msg_text(m)[:2000] for m in reversed(msgs) if isinstance(m, dict) and m.get('role') == 'user'), '')})          # fix pass 5a request log
            if st in (400, 404) and body.get('vision') and not loc and re.search(r'image|vision|modalit', json.dumps(d if isinstance(d, (dict, list)) else str(d))[:900], re.I):
                return jsonify({'ok': False, 'error': 'no_vision', 'model': model, 'message': 'The Copilot model (%s) cannot read pictures, so the picture check was skipped.' % model})
            if st == 200:
                st, d = 502, {'error': {'message': (d.get('error') or {}).get('message', 'empty response') if isinstance(d, dict) else 'empty'}}
            return jsonify(_err(st, d)), (429 if st == 429 else 502)
        ch = d['choices'][0]
        msg = ch.get('message') or {}
        u = d.get('usage') or {}
        cost = u.get('cost')
        try:
            cost = float(cost) if cost is not None else 0.0
        except Exception:
            cost = 0.0
        day = _ledger_add(cost, u.get('prompt_tokens', 0), u.get('completion_tokens', 0))
        log('chat model=%s in=%s out=%s cost=$%.5f %.1fs' % (model, u.get('prompt_tokens'), u.get('completion_tokens'), cost, time.time() - t0))
        content, tcalls, finish = msg.get('content'), msg.get('tool_calls'), ch.get('finish_reason')
        try:                                                            # FIRSTTEST: tool calls written as DSML text -> real calls (when none came back) / stripped
            names = set(((t.get('function') or {}).get('name')) for t in (tools or []) if isinstance(t, dict)) if isinstance(tools, list) else set()
            parsed, content = _dsml_split(content, names)
            if parsed and not tcalls and names:
                tcalls, finish = parsed, 'tool_calls'
                log('chat model=%s: %d tool call(s) written as DSML text parsed into real calls' % (model, len(parsed)))
            elif content != msg.get('content'):
                log('chat model=%s: DSML tool markup stripped from the reply' % model)
        except Exception:
            content = msg.get('content')
        try:                                                            # fix pass 5a request log: what the model was asked and what it answered / called
            _turnlog({'kind': 'chat', 'model': d.get('model') or model, 'vision': bool(body.get('vision')), 'n_msgs': len(msgs), 'cost': cost,
                      'user': next((_msg_text(m)[:2000] for m in reversed(msgs) if isinstance(m, dict) and m.get('role') == 'user'), ''),
                      'reply': str(content or '')[:2000], 'finish': finish,
                      'tool_calls': [{'name': (t.get('function') or {}).get('name'), 'args': str((t.get('function') or {}).get('arguments') or '')[:1500]} for t in (tcalls or []) if isinstance(t, dict)]})
        except Exception:
            pass
        return jsonify({'ok': True, 'message': {'role': 'assistant', 'content': content, 'tool_calls': tcalls},
                        'finish': finish, 'model': d.get('model') or model,
                        'usage': {'prompt': u.get('prompt_tokens', 0), 'completion': u.get('completion_tokens', 0), 'cost': cost},
                        'today': {'cost': day['cost'], 'calls': day['calls']}})

    @app.route('/api/ai/turn-log', methods=['POST'])
    def ai_turn_log():                                     # fix pass 5a: one line per typed copilot turn, posted by the page (local file only, never sent anywhere)
        g = guard()
        if g:
            return g
        raw = request.get_data(as_text=True) or ''
        if len(raw) > 400_000:
            return jsonify({'ok': False, 'error': 'too_big'}), 413
        try:
            rec = json.loads(raw)
        except Exception:
            return jsonify({'ok': False, 'error': 'bad_json'}), 400
        if not isinstance(rec, dict):
            return jsonify({'ok': False, 'error': 'bad_json'}), 400
        rec['kind'] = 'turn'
        _turnlog(rec)
        return jsonify({'ok': True})

    @app.route('/api/ai/test', methods=['POST'])
    def ai_test():
        g = guard()
        if g:
            return g
        key = _get_key()
        if not key:
            return jsonify({'ok': False, 'error': 'no_key', 'message': 'Add your OpenRouter key first.'}), 400
        s = _load_settings()
        model = (s.get('localModel') if _is_local(s) else None) or s.get('model') or DEFAULT_MODEL
        t0 = time.time()
        st, d = _http('POST', '/chat/completions', key, {'model': model, 'max_tokens': 12, **({} if _is_local(s) else {'usage': {'include': True}}),
                                                         'messages': [{'role': 'user', 'content': 'Reply with the single word: ready'}]}, 40)
        if st != 200 or not isinstance(d, dict) or not d.get('choices'):
            return jsonify(_err(st, d)), 502
        u = d.get('usage') or {}
        try:
            cost = float(u.get('cost') or 0)
        except Exception:
            cost = 0.0
        _ledger_add(cost, u.get('prompt_tokens', 0), u.get('completion_tokens', 0))
        return jsonify({'ok': True, 'model': d.get('model') or model, 'reply': (d['choices'][0].get('message') or {}).get('content'), 'ms': int((time.time() - t0) * 1000), 'cost': cost})

    return app
