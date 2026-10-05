"""
Export canonical finish IDs from paint-booth-1-data.js into finish_ids_canonical.json.
Single source of truth for thumbnails/registries: run after editing 1-data.js.

Usage (from V5 folder):
  python scripts/export_finish_ids.py

Output: finish_ids_canonical.json with { "bases": [...], "patterns": [...], "specials": [...] }
"""
import json
import os
import re
import sys

V5_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(V5_ROOT, "paint-booth-1-data.js")
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


def main():
    if not os.path.isfile(DATA_JS):
        print(f"Not found: {DATA_JS}", file=sys.stderr)
        sys.exit(1)
    data = extract_ids_from_js(DATA_JS)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {OUT_JSON}: {len(data['bases'])} bases, {len(data['patterns'])} patterns, {len(data['specials'])} specials")


if __name__ == "__main__":
    main()
