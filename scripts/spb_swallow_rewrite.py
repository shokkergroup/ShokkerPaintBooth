# -*- coding: utf-8 -*-
"""spb_swallow_rewrite.py -- turn silent `except ...: pass/continue` handlers into counted ones.

Rewrites, mechanically and reversibly, every exception handler whose ENTIRE body is a single
``pass`` or ``continue`` into one that first calls ``_spb_swallow("<function>@L<line>", <exc>)``.
Behaviour is unchanged (the exception is still swallowed); the site is counted and logged.
See server_routes/_swallow.py and codebase-health finding F4 (2026-09-05).

Conservative by construction:
  * AST-located, text-edited bottom-up, then re-parsed: the handler count must be identical
    before and after, and no bare-silent handler may remain in a rewritten file.
  * Handlers nested two or more loops deep are left alone (a log call per inner iteration could
    cost time); ``--include-loops`` overrides.
  * ``except:`` becomes ``except BaseException as _spb_ex:`` (identical semantics).
  * Each target file gets the helper import once, right after its first import block.

    python scripts/spb_swallow_rewrite.py server.py server_routes            # dry run (report)
    python scripts/spb_swallow_rewrite.py server.py server_routes --apply    # write
"""
from __future__ import annotations

import ast
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
IMPORT_LINE = "from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows\n"


def _targets(args):
    for a in args:
        p = os.path.join(ROOT, a)
        if os.path.isfile(p) and p.endswith(".py"):
            yield p
        elif os.path.isdir(p):
            for fn in sorted(os.listdir(p)):
                if fn.endswith(".py") and not fn.startswith("_swallow"):
                    yield os.path.join(p, fn)


def _silent_handlers(tree):
    """Yield (handler, enclosing_fn_name, loop_depth) for handlers whose body is only pass/continue."""
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        body = node.body
        if len(body) != 1 or not isinstance(body[0], (ast.Pass, ast.Continue)):
            continue
        fn = "<module>"
        loops = 0
        p = parents.get(node)
        while p is not None:
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn == "<module>":
                fn = p.name
            if isinstance(p, (ast.For, ast.While, ast.AsyncFor)):
                loops += 1
            p = parents.get(p)
        yield node, fn, loops


def rewrite(path: str, apply: bool, include_loops: bool) -> tuple[int, int, int]:
    src = open(path, encoding="utf-8", errors="surrogateescape").read()
    nl = "\r\n" if "\r\n" in src[:5000] else "\n"
    lines = src.split("\n")
    tree = ast.parse(src)
    n_before = sum(isinstance(n, ast.ExceptHandler) for n in ast.walk(tree))
    edits = []  # (line_index, new_text)
    skipped = 0
    for h, fn, loops in _silent_handlers(tree):
        if loops >= 2 and not include_loops:
            skipped += 1
            continue
        stmt = h.body[0]
        tag = f"{fn}@L{h.lineno}"
        # 1) the except line: make sure the exception is bound to a name
        li = h.lineno - 1
        line = lines[li]
        name = h.name
        if name is None:
            if h.type is None:
                m = re.match(r"^(\s*)except\s*:", line)
                if not m:
                    skipped += 1
                    continue
                line = line[:m.end(1)] + "except BaseException as _spb_ex:" + line[m.end():]
            else:
                # insert " as _spb_ex" right after the type expression (same line only)
                if h.type.end_lineno != h.lineno:
                    skipped += 1
                    continue
                col = h.type.end_col_offset
                bline = line.encode("utf-8", "surrogateescape")
                line = (bline[:col] + b" as _spb_ex" + bline[col:]).decode("utf-8", "surrogateescape")
            name = "_spb_ex"
            edits.append((li, line))
        # 2) the body statement
        bi = stmt.lineno - 1
        bline = lines[bi]
        col = stmt.col_offset
        b = bline.encode("utf-8", "surrogateescape")
        if isinstance(stmt, ast.Pass):
            new = b[:col] + f"_spb_swallow({tag!r}, {name})".encode("utf-8") + b[col + 4:]
        else:  # continue
            new = b[:col] + f"_spb_swallow({tag!r}, {name}); ".encode("utf-8") + b[col:]
        edits.append((bi, new.decode("utf-8", "surrogateescape")))
    if not edits:
        return 0, skipped, n_before
    # apply bottom-up (line replacements; indices stable)
    for li, text in edits:
        lines[li] = text
    out = "\n".join(lines)
    # 3) helper import once, after the first top-level import statement
    if "_spb_swallow" in out and "from server_routes._swallow import" not in out:
        t2 = ast.parse(out)
        first_import_end = None
        for node in t2.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                first_import_end = node.end_lineno
            elif first_import_end is not None:
                break
        idx = (first_import_end or 0)
        lines2 = out.split("\n")
        lines2.insert(idx, IMPORT_LINE.rstrip("\n"))
        out = "\n".join(lines2)
    t3 = ast.parse(out)  # must still parse
    n_after = sum(isinstance(n, ast.ExceptHandler) for n in ast.walk(t3))
    assert n_after == n_before, f"{path}: handler count changed {n_before}->{n_after}"
    remaining = sum(1 for h, fn, loops in _silent_handlers(t3) if not (loops >= 2 and not include_loops))
    assert remaining == 0, f"{path}: {remaining} silent handler(s) remain"
    if apply:
        d = os.path.dirname(path)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".swallow-", suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(out.replace("\r\n", "\n").replace("\n", nl).encode("utf-8", "surrogateescape"))
        os.replace(tmp, path)
    return len([e for e in edits if "_spb_swallow(" in e[1]]), skipped, n_before


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    apply = "--apply" in argv
    include_loops = "--include-loops" in argv
    args = [a for a in argv if not a.startswith("--")] or ["server.py", "server_routes"]
    total = 0
    for p in _targets(args):
        n, skipped, handlers = rewrite(p, apply, include_loops)
        if n or skipped:
            print(f"{'WROTE ' if apply else 'DRY   '}{os.path.relpath(p, ROOT):55s} rewrote {n:3d} silent handler(s), skipped {skipped} (loop-nested), {handlers} handlers total")
        total += n
    print(f"SWALLOW REWRITE: {total} site(s) {'written' if apply else 'would be rewritten'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
