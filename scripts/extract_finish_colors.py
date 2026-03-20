"""
Extract finish color definitions from paint-booth-1-data.js into finish_colors.json.
Run from V5 folder: python scripts/extract_finish_colors.py
Output: finish_colors.json (finish_id -> {c1, c2, c3?, ghost?} with color names).
"""
import json
import os
import re
import sys

V5_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(V5_ROOT, "paint-booth-1-data.js")
OUT_JSON = os.path.join(V5_ROOT, "finish_colors.json")


def extract_array(content, array_name):
    """Find ARRAY_NAME = [ ... ]; and return list of parsed rows."""
    marker = "const " + array_name + " = ["
    idx = content.find(marker)
    if idx == -1:
        return []
    start = content.index("[", idx)
    depth = 0
    i = start
    in_string = None
    escape = False
    while i < len(content):
        ch = content[i]
        if escape:
            escape = False
            i += 1
            continue
        if ch == "\\" and in_string:
            escape = True
            i += 1
            continue
        if in_string:
            if ch == in_string:
                in_string = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_string = ch
            i += 1
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        i += 1
    block = content[start : i + 1]
    out = []
    for line in block.split("\n"):
        line = line.strip().rstrip(",").strip()
        if not line or line == "[" or line == "]":
            continue
        try:
            row = json.loads(line)
            if isinstance(row, list) and len(row) >= 3:
                out.append(row)
        except json.JSONDecodeError:
            continue
    return out


def main():
    if not os.path.isfile(DATA_JS):
        print(f"Not found: {DATA_JS}", file=sys.stderr)
        sys.exit(1)
    with open(DATA_JS, "r", encoding="utf-8") as f:
        content = f.read()

    result = {}

    # GRADIENT_DEFS: [id, name, c1, c2]
    for row in extract_array(content, "GRADIENT_DEFS"):
        if len(row) >= 4:
            result[row[0]] = {"c1": row[2], "c2": row[3]}

    # GRADIENT_MIRROR_DEFS: [id, name, c1, c2]
    for row in extract_array(content, "GRADIENT_MIRROR_DEFS"):
        if len(row) >= 4:
            result[row[0]] = {"c1": row[2], "c2": row[3]}

    # GRADIENT_3C_DEFS: [id, name, c1, c2, c3]
    for row in extract_array(content, "GRADIENT_3C_DEFS"):
        if len(row) >= 5:
            result[row[0]] = {"c1": row[2], "c2": row[3], "c3": row[4]}

    # GHOST_GRADIENT_DEFS: [id, name, c1, c2, ghostPattern]
    for row in extract_array(content, "GHOST_GRADIENT_DEFS"):
        if len(row) >= 5:
            result[row[0]] = {"c1": row[2], "c2": row[3], "ghost": row[4]}

    # MC_DEFS: [id, name, [c1,c2,c3], ptype]
    for row in extract_array(content, "MC_DEFS"):
        if len(row) >= 3 and isinstance(row[2], list) and len(row[2]) >= 3:
            result[row[0]] = {"c1": row[2][0], "c2": row[2][1], "c3": row[2][2]}

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {len(result)} finish color entries to {OUT_JSON}")


if __name__ == "__main__":
    main()
