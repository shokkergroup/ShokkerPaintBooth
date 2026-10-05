# -*- coding: utf-8 -*-
"""spb_encoding_lint.py -- find the source of the mojibake (report-only, <3 s, no engine boot).

Codebase-health finding F10 (2026-09-05): 3,453 double-encoded UTF-8 sequences live in
engine/spec_patterns.py, server.py and three other files. The "tool in the chain" is Python
itself on this machine: `sys.flags.utf8_mode == 0`, `locale.getpreferredencoding() == 'cp1252'`,
and ~400 first-party `open()` calls have no `encoding=`. Any script that reads a UTF-8 file that
way and writes it back double-encodes every non-ASCII character. Printing a finish name with an
em-dash through such a stdout raises UnicodeEncodeError ('charmap') -- the crash several agents
hit this week.

Fix policy (owner-safe): the launchers export PYTHONIOENCODING=utf-8 (stdout/stderr only; it
does NOT change how existing cp1252-written files are read), and every text-mode open() gets an
explicit encoding as its file is touched. This lint lists the remaining sites so that happens
deliberately. It never edits anything.

    python scripts/spb_encoding_lint.py                 # summary per file
    python scripts/spb_encoding_lint.py --sites FILE    # every site in one file
    python scripts/spb_encoding_lint.py --gate N        # exit 1 if more than N sites remain
"""
from __future__ import annotations

import ast
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SCAN = ["server.py", "server_v5.py", "spb_server_supervisor.py", "shokker_engine_v2.py", "config.py",
        "server_routes", "engine", "scripts"]
SKIP_DIRS = {"__pycache__", "_archive", "node_modules", "electron-app", "python", "tests"}


def _is_binary_mode(call: ast.Call) -> bool:
    mode = None
    if len(call.args) >= 2:
        mode = call.args[1]
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = kw.value
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return "b" in mode.value
    return False


def scan_file(path: str):
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src, filename=path)
    except Exception:
        return []
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
        if name not in ("open", "read_text", "write_text"):
            continue
        if isinstance(f, ast.Attribute) and name == "open" and not (isinstance(f.value, ast.Name) and f.value.id in ("io", "codecs")):
            # Path.open(...) counts; foo.open(...) on unknown objects is skipped
            if not (isinstance(f.value, ast.Name) and f.value.id[:1].isupper()):
                pass
        if name == "open" and _is_binary_mode(node):
            continue
        if any(kw.arg == "encoding" for kw in node.keywords):
            continue
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "codecs":
            continue
        hits.append(node.lineno)
    return hits


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--sites" in argv:
        target = argv[argv.index("--sites") + 1]
        for ln in scan_file(target):
            print(f"{target}:{ln}")
        return 0
    per_file = Counter()
    files = []
    for entry in SCAN:
        p = os.path.join(ROOT, entry)
        if os.path.isfile(p):
            files.append(p)
        elif os.path.isdir(p):
            for dp, dns, fns in os.walk(p):
                dns[:] = [d for d in dns if d not in SKIP_DIRS]
                files.extend(os.path.join(dp, fn) for fn in fns if fn.endswith(".py"))
    for p in files:
        n = len(scan_file(p))
        if n:
            per_file[os.path.relpath(p, ROOT)] = n
    total = sum(per_file.values())
    for f, n in per_file.most_common(25):
        print(f"{n:4d}  {f}")
    print(f"ENCODING LINT: {total} text-mode open()/read_text/write_text call(s) without encoding= in {len(per_file)} file(s)")
    print("python here: utf8_mode=%d preferred=%s" % (sys.flags.utf8_mode, __import__('locale').getpreferredencoding(False)))
    if "--gate" in argv:
        cap = int(argv[argv.index("--gate") + 1])
        if total > cap:
            print(f"FAIL: {total} > {cap}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
