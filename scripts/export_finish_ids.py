"""
Export canonical finish IDs from paint-booth-0-finish-data.js into finish_ids_canonical.json.
Single source of truth for thumbnails/registries: run after editing 0-finish-data.js.

Usage (from V5 folder):
  python scripts/export_finish_ids.py

Output: finish_ids_canonical.json with { "bases": [...], "patterns": [...], "specials": [...] }
"""
import json
import os
import re
import subprocess
import sys

V5_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# SPB-105 NU-25-LIVE-1 (2026-08-27): the arrays moved to 0-finish-data.js
# long ago; pointing at 1-data.js silently exported three empty collections.
DATA_JS = os.path.join(V5_ROOT, "paint-booth-0-finish-data.js")
OUT_JSON = os.path.join(V5_ROOT, "finish_ids_canonical.json")


def extract_ids_from_js(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Extract from arrays of objects: { id: "foo", ... } or { id: 'foo', ... }
    id_re = re.compile(r'\bid\s*:\s*["\']([a-z][a-z0-9_]*)["\']', re.IGNORECASE)
    # Also from group arrays: "group": ["id1", "id2"] - match quoted ids that look like finish ids
    quoted_id_re = re.compile(r'["\']([a-z][a-z0-9_]*)["\']')

    bases = []
    patterns = []
    specials = []

    # Find const BASES = [ ... ]; and collect ids
    for const_name, out_list in [("const BASES", bases), ("const PATTERNS", patterns), ("const MONOLITHICS", specials)]:
        start = text.find(const_name)
        if start == -1:
            continue
        bracket = text.find("[", start)
        if bracket == -1:
            continue
        depth = 1
        i = bracket + 1
        while i < len(text) and depth > 0:
            if text[i] == "{":
                obj_start = i
                obj_end = text.find("}", i)
                if obj_end != -1:
                    chunk = text[obj_start:obj_end + 1]
                    for m in id_re.finditer(chunk):
                        out_list.append(m.group(1))
                    i = obj_end + 1
                    continue
            elif text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
            i += 1

    # SPECIAL_GROUPS: collect all ids from group values (arrays of string ids)
    # We have "Group Name": ["id1", "id2", ...]. Get all such ids into specials set then list.
    specials_set = set(specials)  # already from MONOLITHICS
    groups_start = text.find("const SPECIAL_GROUPS = ")
    if groups_start != -1:
        groups_start = text.find("{", groups_start)
        depth = 1
        i = groups_start + 1
        in_array = False
        while i < len(text) and depth > 0:
            if text[i] == "[" and not in_array:
                in_array = True
                arr_start = i
            elif in_array and text[i] == "]":
                arr = text[arr_start:i + 1]
                for m in quoted_id_re.finditer(arr):
                    sid = m.group(1)
                    if sid not in ("none", "true", "false") and sid[0].isalpha():
                        specials_set.add(sid)
                in_array = False
            elif text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1

    specials[:] = sorted(specials_set)
    return {"bases": sorted(set(bases)), "patterns": sorted(set(patterns)), "specials": specials}


def extract_ids_from_live_js(path):
    """Evaluate the same finalized arrays the browser sees.

    The legacy regex walker stopped at nested array literals and missed late
    MONOLITHICS plus Object.assign group packs. Node/vm is already the catalog
    truth mechanism used by regression tests, and fails closed on invalid JS.
    """
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync(process.argv[1], 'utf8');
const ctx = {
  window: {},
  console: { log() {}, warn() {}, error() {} },
  setTimeout() {}, clearTimeout() {},
};
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: process.argv[1], timeout: 10000 });
const bases = vm.runInContext('BASES.map(x => x.id)', ctx);
const patterns = vm.runInContext('PATTERNS.map(x => x.id)', ctx);
const monolithics = vm.runInContext('MONOLITHICS.map(x => x.id)', ctx);
const groups = vm.runInContext('SPECIAL_GROUPS', ctx);
const specials = [...new Set(monolithics.concat(...Object.values(groups || {})))];
process.stdout.write(JSON.stringify({ bases, patterns, specials }));
"""
    result = subprocess.run(
        ["node", "-e", script, path],
        cwd=V5_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    data = json.loads(result.stdout)
    return {name: sorted(set(values)) for name, values in data.items()}


def main():
    if not os.path.isfile(DATA_JS):
        print(f"Not found: {DATA_JS}", file=sys.stderr)
        sys.exit(1)
    data = extract_ids_from_live_js(DATA_JS)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {OUT_JSON}: {len(data['bases'])} bases, {len(data['patterns'])} patterns, {len(data['specials'])} specials")


if __name__ == "__main__":
    main()
