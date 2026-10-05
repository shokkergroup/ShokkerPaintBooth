# ============================================================================
# BUMP CACHE TOKENS — safely, for every asset you actually changed
#
# WHY THIS EXISTS
#   paint-booth-v2.html loads every asset as `foo.js?v=<token>`. The browser
#   caches by URL, so an edit that does not move its token ships to nobody.
#   On 2026-07-20 sixteen files shipped stale that way.
#
#   The obvious fix — sed the token — is how this script was born. Doing it by
#   hand with `re.search(r'foo\.js\?v=[^"\']+')` matched a sentence in
#   SPB_WIKI.html that merely MENTIONED the token, and `[^"\']+` ran greedily
#   across two lines to the next apostrophe, deleting 564 characters of a
#   post-mortem. A bump must never be able to touch prose.
#
# THE RULE HERE
#   Rewrite a token ONLY inside a real src="…" / href="…" attribute value.
#   The pattern is anchored on the attribute and stops at the closing quote,
#   so a filename in a sentence, a code span, or a log entry cannot match.
#
# USAGE
#   python scripts/bump_cache_tokens.py                 # audit: what is stale
#   python scripts/bump_cache_tokens.py --write         # bump every stale asset
#   python scripts/bump_cache_tokens.py --write --files paint-booth-3-canvas.js
#   python scripts/bump_cache_tokens.py --write --label grabobject
#
# Staleness is decided by git: an asset is stale when its working-tree content
# differs from HEAD but its token is unchanged from HEAD. That is exactly the
# 2026-07-20 failure, so the audit form is worth running before any handoff.
# ============================================================================
import argparse
import datetime
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSET_SUFFIXES = ('.js', '.css')
# Where assets get referenced. Root + the packaged copy under electron-app/server.
HTML_GLOBS = ('*.html', 'electron-app/server/*.html')


def git(*args):
    r = subprocess.run(('git',) + args, capture_output=True, cwd=str(ROOT))
    return r.stdout.decode('utf-8', 'ignore')


def changed_assets():
    """Assets whose content differs from HEAD (staged or not)."""
    names = set()
    for line in (git('diff', '--name-only', 'HEAD') + '\n' + git('diff', '--name-only')).splitlines():
        line = line.strip()
        if line.endswith(ASSET_SUFFIXES):
            names.add(pathlib.PurePosixPath(line).name)
    return names


def html_files():
    seen = []
    for pat in HTML_GLOBS:
        for p in sorted(ROOT.glob(pat)):
            if p.is_file():
                seen.append(p)
    return seen


def token_pattern(asset):
    """Match `?v=<token>` ONLY inside a src/href attribute value.

    Anchored on the attribute name and closed by the same quote character, so
    the match can never leave the tag — the failure that ate a wiki paragraph.
    """
    return re.compile(
        r'((?:src|href)\s*=\s*(["\'])[^"\']*?'   # attribute, opening quote
        + re.escape(asset) +                     # the asset filename
        r'\?v=)([^"\']*)(\2)'                    # token, then the SAME quote
    )


def tokens_in(text, asset):
    return [m.group(3) for m in token_pattern(asset).finditer(text)]


def new_token(label):
    day = datetime.date.today().strftime('%Y%m%d')
    return 'spb-%s-%s' % (re.sub(r'[^a-z0-9]+', '', (label or 'bump').lower()), day)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='apply (default: audit only)')
    ap.add_argument('--files', help='comma-separated asset basenames; default = git-changed assets')
    ap.add_argument('--label', default='bump', help='slug for the new token')
    # "already bumped this cycle" means "differs from HEAD" — which is NOT the same
    # as "differs from what a browser last cached". Edit a file twice in one day and
    # the second edit ships under a token the browser already has. --force bumps
    # regardless; use it whenever you have just edited the file.
    ap.add_argument('--force', action='store_true',
                    help='bump even if the token already differs from HEAD')
    ap.add_argument('--token', help='exact token to use (overrides --label)')
    a = ap.parse_args()

    if a.files:
        assets = {s.strip() for s in a.files.split(',') if s.strip()}
    else:
        assets = changed_assets()
    if not assets:
        print('no changed assets — nothing to bump')
        return 0

    pages = html_files()
    head_cache = {}

    def head_text(p):
        rel = p.relative_to(ROOT).as_posix()
        if rel not in head_cache:
            head_cache[rel] = git('show', 'HEAD:' + rel)
        return head_cache[rel]

    token = a.token or new_token(a.label)
    stale, fresh, edits = [], [], 0

    for asset in sorted(assets):
        refs = [(p, tokens_in(p.read_text(encoding='utf-8', errors='ignore'), asset)) for p in pages]
        refs = [(p, t) for p, t in refs if t]
        if not refs:
            continue
        # stale = every reference still carries the token HEAD had
        was_bumped = False
        for p, toks in refs:
            for t in toks:
                if t not in tokens_in(head_text(p), asset):
                    was_bumped = True
        (fresh if (was_bumped and not a.force) else stale).append((asset, refs))

    for asset, refs in fresh:
        print('  ok    %-42s already bumped this cycle' % asset)
    for asset, refs in stale:
        where = ', '.join(p.relative_to(ROOT).as_posix() for p, _ in refs)
        print('  STALE %-42s %s' % (asset, where))
        if not a.write:
            continue
        for p, _ in refs:
            s = p.read_text(encoding='utf-8', errors='ignore')
            n = token_pattern(asset).sub(lambda m: m.group(1) + token + m.group(4), s)
            if n != s:
                p.write_text(n, encoding='utf-8')
                edits += 1

    print()
    if a.write:
        print('bumped %d reference site(s) to %s' % (edits, token))
        print('now run: node scripts/sync-runtime-copies.js --write')
    elif stale:
        print('%d stale asset(s). Re-run with --write to bump.' % len(stale))
        return 1
    else:
        print('all changed assets carry a fresh token')
    return 0


if __name__ == '__main__':
    sys.exit(main())
