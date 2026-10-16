"""HELPER V3 stage S9 (local half), 2026-10-06 -- the "this didn't do what I asked" log.

POST /api/ai/feedback   appends ONE record to output/ai_logs/feedback.jsonl (LOCAL ONLY, nothing is sent anywhere;
                        where opt-in feedback is eventually SENT is an open owner decision -- this module has no network code).
GET  /api/ai/feedback   admin view: newest first, ?limit=50 (max 500), ?id=<fb id>, ?turn=<seq>, ?summary=1 (counts only).

A record = turn id + user text + helper reply + the S1+ fields of the matching turn-log record (frame, verify, v3, plan, report,
zones_changed) + undo state + optional comment + the last <= 6 conversation turns. The client (js/spb-feedback.js) only has to send
{seq, text, reply?}: whatever it leaves out is filled in from output/ai_logs/copilot_turns.jsonl (the page already posted the turn there
when the answer finished), so the button never depends on the bubble holding every field.

Scrubbing for SHARING is a separate step (scripts/ai_eval/feedback_to_scenario.py scrubs when it drafts a scenario). The local file is
the owner's own machine and keeps the raw text so a bug can be reproduced.
Registered from server_routes/ai_copilot_routes.py (next to the encyclopedia routes). Read it with: python scripts/ai_eval/feedback_to_scenario.py --show
"""
import datetime as _dt
import json
import os
import secrets
import threading

_FB_MAX = 5 * 1024 * 1024
_FB_KEEP = 4
_FB_LOCK = threading.Lock()
_BODY_MAX = 300_000
_TAIL_BYTES = 4 * 1024 * 1024          # how far back into copilot_turns.jsonl we look for the matching turn

_STR_CAP = {'text': 4000, 'reply': 6000, 'comment': 600, 'app_version': 40, 'car': 80, 'rating': 20, 'source': 40}
_PASS_KEYS = ('frame', 'frames', 'verify', 'v3', 'plan', 'report', 'zones_changed', 'offline', 'builder')


def _log_dir():
    from server_routes.ai_copilot_routes import _turnlog_dir
    return _turnlog_dir()


def _fb_path():
    return os.path.join(_log_dir(), 'feedback.jsonl')


def _tail_records(path, nbytes=_TAIL_BYTES):
    """The last records of a jsonl file (newest last); a partial first line is dropped."""
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as f:
            if size > nbytes:
                f.seek(size - nbytes)
                f.readline()
            data = f.read()
    except OSError:
        return []
    out = []
    for ln in data.decode('utf-8', 'replace').splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def _ai_reply_from(rec):
    for m in reversed(rec.get('replies') or []):
        if isinstance(m, dict) and m.get('role') == 'ai' and m.get('text'):
            return str(m['text'])
    return ''


def _plan_from_frame(frame, zones):
    """plan = op verbs + target + zone ids (the shape the S9 spec asks for)."""
    ops = []
    for o in (frame or {}).get('ops') or []:
        if not isinstance(o, dict):
            continue
        t = o.get('target') or {}
        ops.append({'verb': o.get('verb'), 'target': {k: t.get(k) for k in ('kind', 'parts', 'layers', 'element') if t.get(k)}})
    zids = [z.get('id') or z.get('name') for z in (zones or []) if isinstance(z, dict) and (z.get('id') or z.get('name'))]
    return {'ops': ops, 'zones': zids[:24]} if (ops or zids) else None


def _find_turn(recs, seq, text):
    """Newest turn-log record with this page seq + text (seq restarts every page load, so the text must match too)."""
    best = by_seq = None
    for r in recs:
        if r.get('kind') != 'turn' or r.get('src') == 'report':
            continue
        if seq is not None and r.get('seq') == seq:
            by_seq = r                                       # Run / chip turns log a synthetic text ("Run: ..."), so seq alone is the fallback
        if text and str(r.get('text') or '').strip() != text.strip():
            continue
        if seq is not None and r.get('seq') != seq:
            continue
        best = r
    return best or by_seq


def _find_report(recs, text, after_ts):
    best = None
    for r in recs:
        if r.get('src') == 'report' and (not text or str(r.get('text') or '').strip() == text.strip()):
            if not after_ts or str(r.get('ts') or '') >= after_ts:
                best = r
    return best


def build_record(body, turn_recs=None, port=None):
    """Pure function (testable without Flask): the client body (+ turn log) -> the stored feedback record."""
    b = body if isinstance(body, dict) else {}
    rec = {'id': 'fb-%s-%s' % (_dt.datetime.now().strftime('%Y%m%d%H%M%S'), secrets.token_hex(2)),
           'ts': _dt.datetime.now().isoformat(timespec='seconds'), 'src': 'feedback', 'port': port}
    for k, cap in _STR_CAP.items():
        v = b.get(k)
        if v is not None:
            rec[k] = str(v)[:cap]
    rec.setdefault('rating', 'down')
    tid = b.get('turn_id') if isinstance(b.get('turn_id'), dict) else {}
    seq = b.get('seq', tid.get('seq'))
    try:
        seq = int(seq) if seq is not None else None
    except (TypeError, ValueError):
        seq = None
    frame_turn = b.get('frame_turn') or tid.get('frame_turn') or ((b.get('frame') or {}).get('turn') if isinstance(b.get('frame'), dict) else None)
    rec['turn_id'] = {'seq': seq, 'frame_turn': str(frame_turn)[:20] if frame_turn else None, 'turn_ts': tid.get('ts') or b.get('turn_ts')}
    u = b.get('undo') if isinstance(b.get('undo'), dict) else {}
    rec['undo'] = {'offered': bool(u.get('offered', True)), 'available': u.get('available'), 'done': bool(u.get('done', False)), 'undone_by_button': bool(u.get('undone_by_button', False))}
    for k in _PASS_KEYS:
        if b.get(k) is not None:
            rec[k] = b[k]
    cv = b.get('convo')
    if isinstance(cv, list):
        rec['convo'] = [{'role': str((m or {}).get('role') or '')[:12], 'text': str((m or {}).get('text') or '')[:1500]} for m in cv[-6:] if isinstance(m, dict)]
    # enrich from the turn log: only the keys the client did not send
    t = _find_turn(turn_recs or [], seq, rec.get('text', ''))
    rec['matched_turn'] = bool(t)
    if t:
        if not rec.get('text'):
            rec['text'] = str(t.get('text') or '')[:4000]
        if not rec.get('reply'):
            rec['reply'] = _ai_reply_from(t)[:6000]
        for k in _PASS_KEYS:
            if rec.get(k) is None and t.get(k) is not None:
                rec[k] = t[k]
        if rec.get('verify') is None and isinstance(rec.get('frame'), dict) and rec['frame'].get('verify'):
            rec['verify'] = rec['frame']['verify']
        if not rec['turn_id'].get('frame_turn') and isinstance(t.get('frame'), dict):
            rec['turn_id']['frame_turn'] = t['frame'].get('turn')
        rec['turn_id']['turn_ts'] = rec['turn_id'].get('turn_ts') or t.get('ts')
        if rec.get('report') is None:
            rp = _find_report(turn_recs or [], rec.get('text', ''), t.get('ts'))
            if rp and rp.get('report') is not None:
                rec['report'] = rp['report']
        t_src = t.get('src')
        if t_src:
            rec['turn_src'] = t_src
    if rec.get('plan') is None:
        pl = _plan_from_frame(rec.get('frame'), rec.get('zones_changed'))
        if pl:
            rec['plan'] = pl
    return rec


def _append(rec):
    line = json.dumps(rec, ensure_ascii=False, default=str)
    if len(line) > 250_000:                                  # never refuse the owner's report: drop the heavy optional blobs first
        for k in ('builder', 'offline', 'frames', 'zones_changed', 'report'):
            rec.pop(k, None)
        rec['trimmed'] = True
        line = json.dumps(rec, ensure_ascii=False, default=str)
    with _FB_LOCK:
        p = _fb_path()
        if os.path.exists(p) and os.path.getsize(p) > _FB_MAX:
            for i in range(_FB_KEEP - 1, 0, -1):
                a, b = '%s.%d' % (p, i), '%s.%d' % (p, i + 1)
                if os.path.exists(a):
                    os.replace(a, b)
            os.replace(p, p + '.1')
        with open(p, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    return rec


def register_ai_feedback_routes(app, logger=None):
    from flask import jsonify, request

    def guard():
        from server_routes.ai_copilot_routes import _origin_ok
        if not _origin_ok(request):
            return jsonify({'ok': False, 'error': 'origin', 'message': 'Blocked: AI routes are for the Shokker app only.'}), 403
        return None

    @app.route('/api/ai/feedback', methods=['POST'])
    def ai_feedback_post():
        g = guard()
        if g:
            return g
        raw = request.get_data(as_text=True) or ''
        if len(raw) > _BODY_MAX:
            return jsonify({'ok': False, 'error': 'too_big'}), 413
        try:
            body = json.loads(raw)
        except Exception:
            return jsonify({'ok': False, 'error': 'bad_json'}), 400
        if not isinstance(body, dict):
            return jsonify({'ok': False, 'error': 'bad_json'}), 400
        port = None
        try:
            port = int(str(request.host or '').rsplit(':', 1)[-1])
        except Exception:
            port = None
        try:
            turns = _tail_records(os.path.join(_log_dir(), 'copilot_turns.jsonl'))
            rec = _append(build_record(body, turns, port))
        except Exception as e:                               # never take the panel down
            if logger:
                try:
                    logger.warning('[ai-feedback] write failed: %s', e)
                except Exception:
                    pass
            return jsonify({'ok': False, 'error': 'write_failed', 'message': str(e)[:200]}), 500
        return jsonify({'ok': True, 'id': rec['id'], 'matched_turn': rec.get('matched_turn', False), 'stored': 'local'})

    @app.route('/api/ai/feedback', methods=['GET'])
    def ai_feedback_get():
        g = guard()
        if g:
            return g
        try:
            limit = max(1, min(500, int(request.args.get('limit') or 50)))
        except ValueError:
            limit = 50
        recs = _tail_records(_fb_path(), 16 * 1024 * 1024)
        fid, turn = (request.args.get('id') or '').strip(), (request.args.get('turn') or '').strip()
        if fid:
            recs = [r for r in recs if r.get('id') == fid]
        if turn:
            recs = [r for r in recs if str((r.get('turn_id') or {}).get('seq')) == turn or (r.get('turn_id') or {}).get('frame_turn') == turn]
        counts = {'total': len(recs), 'with_frame': sum(1 for r in recs if r.get('frame')), 'undone': sum(1 for r in recs if (r.get('undo') or {}).get('done')),
                  'with_comment': sum(1 for r in recs if r.get('comment'))}
        if request.args.get('summary'):
            return jsonify({'ok': True, 'counts': counts})
        return jsonify({'ok': True, 'counts': counts, 'records': list(reversed(recs))[:limit], 'file': 'output/ai_logs/feedback.jsonl'})
