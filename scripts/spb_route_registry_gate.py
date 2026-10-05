# -*- coding: utf-8 -*-
"""spb_route_registry_gate.py -- catch duplicate Flask routes BEFORE a restart (no engine boot, <2 s).

Codebase-health finding F11 (2026-09-05): the live app is server_v5.py's Flask instance; it
inherits server.py's URL rules by copying them (server_v5.py ~911-947), so a path defined in
BOTH places never raises -- werkzeug just serves whichever was registered first. Eight such
shadows exist today and are resolved purely by import order. Nothing declared that intent, so
the next duplicate will be another silent accident.

This gate parses every `@app.route(...)` / `@<x>.route(...)` decorator in server.py,
server_v5.py and server_routes/*.py with `ast`, groups them by (path, method), and:

  * prints every (path, method) defined more than once, with the sites;
  * exits 0 if the set of duplicates is exactly the KNOWN_SHADOWS allow-list below
    (each entry has the owner-decision it is waiting on);
  * exits 1 for any NEW duplicate, or if a known shadow disappears (update the list -- that
    is a reviewable act, same pattern as protected_finishes.json / COVERAGE_EXEMPT).

    python scripts/spb_route_registry_gate.py          # gate
    python scripts/spb_route_registry_gate.py --all    # also print every route (path, methods, site)
"""
from __future__ import annotations

import ast
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# (path, method) -> why it is allowed to exist twice today. Winner = first registered = server_v5.py.
KNOWN_SHADOWS = {
    ("/", "GET"): "server_v5.py:475 wins; static_pages.py:26 is in server_v5's inherit skip-set",
    ("/<path:filename>", "GET"): "server_v5.py:457 wins; asset_routes.py:27 is in the skip-set",
    ("/build-check", "GET"): "server_v5.py:639 wins; system_status.py:38 is in the skip-set",
    ("/status", "GET"): "server_v5.py:855 wins; system_status.py:63 is in the skip-set",
    ("/api/finish-data", "GET"): "server_v5.py:661 wins by werkzeug order; finish_catalog_routes.py:226 has extra features (cache, ?type) -- OWNER DECISION which body wins",
    ("/api/health", "GET"): "server_v5.py:800 wins by order; diagnostics.py:108 adds uptime/rid -- OWNER DECISION",
    ("/finish-viewer.html", "GET"): "server_v5.py:496 wins by order; static_pages.py:56 shadowed -- OWNER DECISION",
    ("/api/finish-viewer/mono/<finish_id>", "GET"): "server_v5.py:574 wins by order; finish_viewer_render_routes.py:237 shadowed -- OWNER DECISION",
}


def _files():
    yield os.path.join(ROOT, "server.py")
    yield os.path.join(ROOT, "server_v5.py")
    d = os.path.join(ROOT, "server_routes")
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".py"):
            yield os.path.join(d, fn)


def _const_str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def collect():
    sites = defaultdict(list)  # (path, method) -> [file:line fn]
    for path in _files():
        try:
            tree = ast.parse(open(path, encoding="utf-8", errors="replace").read(), filename=path)
        except SyntaxError as ex:
            print(f"PARSE-ERROR {os.path.relpath(path, ROOT)}: {ex}")
            continue
        rel = os.path.relpath(path, ROOT)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "route"):
                    continue
                if not dec.args:
                    continue
                route = _const_str(dec.args[0])
                if route is None:
                    continue
                methods = ["GET"]
                for kw in dec.keywords:
                    if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                        methods = [m for m in (_const_str(e) for e in kw.value.elts) if m]
                for m in methods:
                    sites[(route, m.upper())].append(f"{rel}:{node.lineno} {node.name}")
    return sites


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    sites = collect()
    if "--all" in argv:
        for (route, m), where in sorted(sites.items()):
            print(f"{m:6s} {route:55s} {' | '.join(where)}")
    dups = {k: v for k, v in sites.items() if len(v) > 1}
    new = {k: v for k, v in dups.items() if k not in KNOWN_SHADOWS}
    gone = [k for k in KNOWN_SHADOWS if k not in dups]
    for k, v in sorted(dups.items()):
        tag = "KNOWN  " if k in KNOWN_SHADOWS else "NEW    "
        print(f"{tag} {k[1]:6s} {k[0]:50s} {' | '.join(v)}")
    for k in gone:
        print(f"GONE    {k[1]:6s} {k[0]:50s} (no longer duplicated -- remove it from KNOWN_SHADOWS)")
    n_routes = len(sites)
    print(f"ROUTE GATE: {n_routes} (path,method) rules, {len(dups)} duplicated ({len(new)} new, {len(gone)} stale allow-list) -> "
          f"{'FAIL' if (new or gone) else 'PASS'}")
    return 1 if (new or gone) else 0


if __name__ == "__main__":
    sys.exit(main())
