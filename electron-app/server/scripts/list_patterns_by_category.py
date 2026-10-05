#!/usr/bin/env python3
"""
List pattern IDs by UI category (from paint-booth-1-data.js PATTERN_GROUPS).
Use this to see which patterns live in which category when rebuilding or overriding.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(ROOT, "paint-booth-1-data.js")


def main():
    if not os.path.isfile(DATA_JS):
        print(f"Not found: {DATA_JS}")
        sys.exit(1)
    with open(DATA_JS, "r", encoding="utf-8") as f:
        content = f.read()
    # Find PATTERN_GROUPS block
    start = content.find("const PATTERN_GROUPS = {")
    if start == -1:
        print("PATTERN_GROUPS not found in paint-booth-1-data.js")
        sys.exit(1)
    block = content[start:start + 20000]
    end = block.find("\n};")
    if end != -1:
        block = block[: end + 1]
    # Parse lines like:    "Category Name": ["id1", "id2", ...],
    pattern = re.compile(r'\s*"([^"]+)":\s*\[(.*?)\]\s*,?\s*$', re.MULTILINE | re.DOTALL)
    # Simpler: line by line for "    \"...\": ["
    groups = {}
    for line in block.splitlines():
        line = line.strip()
        if line.startswith('"') and '":' in line:
            idx = line.index('":')
            name = line[1:idx].strip('"')
            rest = line[idx + 2:].strip()
            if rest.startswith("["):
                ids_str = rest[1:]
                if ids_str.endswith("],"):
                    ids_str = ids_str[:-2]
                elif ids_str.endswith("]"):
                    ids_str = ids_str[:-1]
                ids = [x.strip().strip('"') for x in ids_str.split(",") if x.strip()]
                groups[name] = ids
    for cat, ids in sorted(groups.items()):
        print(f"\n{cat} ({len(ids)} patterns)")
        for pid in ids:
            print(f"  {pid}")
    print()


if __name__ == "__main__":
    main()
