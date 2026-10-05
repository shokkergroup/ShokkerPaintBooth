"""Shared "hidden feature" filter for every Encyclopedia generator (owner rule 2026-10-04: Easy mode is hidden, nothing may talk about it).
One list: scripts/ai_atlas/enc_hidden_features.json. Import this module from a generator:

    from enc_hidden import is_hidden_record, is_hidden_article_id, scrub, scrub_obj, mentions, HIDDEN

* is_hidden_record(rec)      -> True for inventory records that ARE the hidden feature (dropped from coverage, no article).
* is_hidden_article_id(id)   -> True for article / page ids that belong to the hidden feature (never written).
* scrub(text)                -> the text with the hidden feature's names rewritten ("PRO / CHAT / EASY pill" -> "PRO / CHAT pill") and every
                                sentence that is ABOUT the hidden feature removed. Returns '' when nothing is left.
* scrub_obj(obj)             -> same for every string inside a record / list / dict (list items that scrub to '' are dropped; ids and sources untouched).
* mentions(text)             -> True when the text still names the hidden feature (the gate regex list in the JSON).
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / 'enc_hidden_features.json').read_text(encoding='utf-8'))
HIDDEN = list(CFG.get('features') or [])
_ON = 'easy_mode' in HIDDEN

_ID_RES = [re.compile(p) for p in CFG.get('hidden_record_ids', [])]
_PREFIXES = tuple(CFG.get('hidden_article_prefixes', []))
_GATE = [re.compile(p['re'], re.I if 'i' in (p.get('flags') or '') else 0) for p in CFG.get('gate_text_patterns', [])]

# any use of the word that is NOT the plain adjective ("easy to", "easy way", "easier", "easily", "easy enough", "so easy")
_EASY_WORD = re.compile(r"\b[Ee]asy\b(?![\s-]*(?:to|way|for|enough|and|swap|contrast|ground|background|dark|bright|pairing|pairs|win|fix|one|job|read|reading))|\bEasiest\b")
_FEATURE_SENT = re.compile(r"\bEasy\b|\bEASY\b|\beasy[\s-]*mode\b|paint[\s-]*by[\s-]*numbers|\bTell bar\b|\bREADY TO RACE\b|\bWHERE IT GOES\b|\bSAVE TO iRACING\b|\bBIGGER PICTURE\b|colou?r-parts rail", re.I)


def is_hidden_record(rec):
    if not _ON:
        return False
    if rec.get('domain') in CFG.get('hidden_domains', []):
        return True
    rid = rec.get('id') or ''
    return any(r.search(rid) for r in _ID_RES)


def is_hidden_id(rid):
    return bool(_ON and any(r.search(rid or '') for r in _ID_RES))


def is_hidden_article_id(aid):
    if not _ON:
        return False
    a = aid or ''
    return a.startswith(_PREFIXES) or ('.easy.' in a) or a.startswith('easy.') or a.startswith('controls_easy')


def mentions(text):
    if not _ON or not isinstance(text, str):
        return False
    return any(r.search(text) for r in _GATE)


# --- rewriting -------------------------------------------------------------------------------------------------------------------------
_REWRITES = [
    (re.compile(r",\s*or go to EASY:[^.]*\."), '.'),
    (re.compile(r"\bEASY\s+(?:or|and)\s+CHAT\b"), 'CHAT'),
    (re.compile(r"\bPRO\s*/\s*CHAT\s*/\s*EASY\b"), 'PRO / CHAT'),
    (re.compile(r"\bPRO\s*\|\s*CHAT\s*\|\s*EASY\b"), 'PRO | CHAT'),
    (re.compile(r"\bPRO,\s*CHAT,?\s*(?:and|or)\s*EASY\b"), 'PRO and CHAT'),
    (re.compile(r"\bPRO,\s*CHAT\s*(?:and|or)\s*EASY\b"), 'PRO and CHAT'),
    (re.compile(r"\bPRO\s*(?:and|or|/|\|)\s*EASY\b"), 'PRO'),
    (re.compile(r"\bCHAT,?\s*(?:and|or)\s*EASY\b"), 'CHAT'),
    (re.compile(r"\bEASY,\s*CHAT\b"), 'CHAT'),
    (re.compile(r"\bPRO\s*MODE\b(?=\s*[-→>])"), 'PRO MODE'),
    (re.compile(r"\bPRO / CHAT / EASY\b"), 'PRO / CHAT'),
]
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'(“])')


def _fix_spaces(s):
    s = re.sub(r"\s+([,.;:!?)])", r"\1", s)
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def scrub(text, broad=False):
    """Rewrite names, then drop every sentence about the hidden feature. broad=True also drops any non-adjective use of the word 'easy'
    (used for the inventory / how-do-I / Getting Started material, where 'Easy' always means the hidden mode)."""
    if not _ON or not isinstance(text, str) or not text:
        return text
    if not (_FEATURE_SENT.search(text) or any(r.search(text) for r in _GATE) or (broad and _EASY_WORD.search(text))):
        return text   # nothing about the hidden feature: never touch the text (no whitespace drift)
    t = text
    for rx, rep in _REWRITES:
        t = rx.sub(rep, t)
    t = _fix_spaces(t)
    parts = _SENT_SPLIT.split(t)
    keep = []
    for p in parts:
        hit = bool(_FEATURE_SENT.search(p)) if broad else any(r.search(p) for r in _GATE)
        if not hit and broad and _EASY_WORD.search(p):
            hit = True
        if not hit:
            keep.append(p)
    if keep and len(keep) < len(parts) and keep[0].startswith('Or ') and parts[0] is not keep[0]:
        keep[0] = keep[0][3:4].upper() + keep[0][4:]    # the sentence it was an alternative to is gone: "Or in the AI panel" -> "In the AI panel"
    return _fix_spaces(' '.join(keep))


_SKIP_KEYS = {'id', 'source', 'sources', 'inv', 'topic', 'covers', 'domain', 'kind', 'file', 'f', 'ui', 'ui_ids', 'key', 'first', 'last'}


def scrub_obj(o, broad=True, key=None):
    if isinstance(o, str):
        if key in _SKIP_KEYS:
            return o
        return scrub(o, broad)
    if isinstance(o, list):
        out = []
        for x in o:
            if isinstance(x, str):
                if key in _SKIP_KEYS or key in ('related', 'ui', 'needs'):
                    if is_hidden_id(x):
                        continue
                    out.append(x)
                    continue
                y = scrub(x, broad)
                if y:
                    out.append(y)
            else:
                out.append(scrub_obj(x, broad, key))
        return out
    if isinstance(o, dict):
        return {k: scrub_obj(v, broad, k) for k, v in o.items()}
    return o


# --- markdown cards + UI-map items (2026-10-05 hidden-feature sweep: spb-self-help.js, spb-ai-knowledge.js, app_map.md, ui_map.json) ----------
def is_hidden_item(it):
    """A UI-map item / panel / mode that IS the hidden feature (its own panel, mode flag or id)."""
    if not _ON or not isinstance(it, dict):
        return False
    if is_hidden_id(it.get('id')) or is_hidden_id(it.get('dom_id')):
        return True
    return it.get('mode') == 'easy' or str(it.get('panel') or '').startswith('easy') or str(it.get('id') or '').startswith('easy')


_TAG_LINE = re.compile(r'^\[([^\]|]+)\|([^\]|]*)\|?(.*)\]\s*$')
_LIST_LINE = re.compile(r'^(\s*)(\d+)\.\s+(.*)$')
_BUL_LINE = re.compile(r'^(\s*[-*]\s+)(.*)$')


def _scrub_tag_line(line):
    """[hdi.x | mode | needs: a | ui: b, c] -> same tag with hidden ui ids removed. Returns None when the entry itself is the hidden feature."""
    m = re.match(r'^\[(hdi\.[\w]+)\s*\|\s*([^|]*)\|(.*)\]\s*$', line.strip())
    if not m:
        return line
    if is_hidden_id(m.group(1)) or m.group(2).strip() == 'easy':
        return None
    def fix(mm):
        ids = [x.strip() for x in mm.group(2).split(',') if x.strip() and not is_hidden_id(x.strip())]
        return mm.group(1) + ', '.join(ids)
    return '[%s | %s |%s]' % (m.group(1), m.group(2).strip(), re.sub(r'(ui:\s*)([^|\]]*)', fix, m.group(3)))


def scrub_md(text):
    """Scrub a markdown card line by line (scrub() alone would collapse the newlines): hidden how-to blocks are dropped, sentences about the hidden
    feature are removed from the rest, numbered steps are renumbered, and a block that has lost all its steps / body is dropped."""
    if not _ON or not isinstance(text, str) or not text:
        return text
    nl = '\r\n' if '\r\n' in text else '\n'
    blocks = re.split(r'\n(?=## )', text.replace('\r\n', '\n'))
    out_blocks = []
    for bi, blk in enumerate(blocks):
        lines = blk.split('\n')
        is_h2 = lines[0].startswith('## ')
        out, dropped_step, nsteps, nbody = [], False, 0, 0
        drop_block = False
        for li, line in enumerate(lines):
            s = line.strip()
            if not s:
                out.append(line)
                continue
            if li <= 2 and s.startswith('[') and s.endswith(']') and '|' in s:
                t = _scrub_tag_line(line)
                if t is None:
                    drop_block = True
                    break
                out.append(t)
                continue
            if s.startswith('#'):
                hs = re.match(r'^(#+\s+)(.*)$', s)
                new = scrub(hs.group(2), True) if hs else s
                if hs and not new:
                    if li == 0:
                        drop_block = True
                        break
                    continue
                out.append((hs.group(1) + new) if hs else s)
                continue
            m = _LIST_LINE.match(line)
            if m:
                nsteps += 1
                new = scrub(m.group(3), True)
                if not new:
                    dropped_step = True
                    continue
                out.append('%s%s. %s' % (m.group(1), m.group(2), new))
                continue
            m = _BUL_LINE.match(line)
            if m:
                new = scrub(m.group(2), True)
                if new:
                    out.append(m.group(1) + new)
                continue
            if s.startswith('Also asked as:'):
                alts = [a.strip() for a in s[len('Also asked as:'):].split(';')]
                alts = [a for a in alts if a and not mentions(a) and not _EASY_WORD.search(a)]
                if alts:
                    out.append('Also asked as: ' + '; '.join(alts))
                continue
            new = scrub(line, True)
            if new:
                out.append(new)
                nbody += 1
        if drop_block:
            continue
        if dropped_step:
            if not any(_LIST_LINE.match(x) for x in out):
                continue                          # every step was about the hidden feature
            n = 0
            for i, x in enumerate(out):
                m = _LIST_LINE.match(x)
                if m:
                    n += 1
                    out[i] = '%s%d. %s' % (m.group(1), n, m.group(3))
        if is_h2 and nsteps == 0 and not [x for x in out[1:] if x.strip()]:
            continue                              # a heading with nothing left under it
        out_blocks.append('\n'.join(out))
    return nl.join(out_blocks)
