"""SPB-89 owner-rating I/O helpers (tick 70).

Extracted from server.py so they can be unit-tested without spinning up Flask
or the engine. Pure file I/O + regex parsing + JS-literal formatting.

The endpoint route in server.py imports these and orchestrates the write +
audit-trail append + JSON response. This module is the testable pure-data
layer.

Doctrine for the JS literal we read/write:
- Each entry is `"<surface>:<id>": { status: "...", source: "...", notes: "...", scores: {...} }`
- Top-level dict is `const PICKER_OWNER_RATINGS = { ... };`
- Entries are sorted by fid for stable diffs

Caller obligations (in server.py):
- Validate inputs before calling _format_rating_entry (status enum, scores keys, etc.)
- Hold the file lock if needed (not necessary on Windows since rename is atomic)
- Append to history JSONL outside this module
"""
from __future__ import annotations

import os
import re
from typing import Dict

VALID_RATING_STATUSES = {"keeper", "watch", "rework_paint", "rework_spec", "reject"}
VALID_SCORE_KEYS = {"patternDesign", "uniqueness", "specDetail", "renderTime",
                    "intentFit", "sponsorSafety", "overall"}

# Surface prefixes that may appear as finish-id keys.
_FID_PAT = re.compile(
    r'"((?:base|monolithic|pattern|spec_pattern):[a-z0-9_]+)"\s*:\s*\{((?:[^{}]|\{[^{}]*\})*)\}',
    flags=re.S,
)


def parse_owner_ratings_js(text: str) -> Dict[str, str]:
    """Extract `{fid: entry_block_text}` from the JS literal source.

    Best-effort regex parse. Returns the raw inner text of each entry — caller
    is responsible for any further parsing of status/scores/notes. Entries we
    can't match are silently skipped (their raw text won't appear in the
    re-emitted file).
    """
    out: Dict[str, str] = {}
    for m in _FID_PAT.finditer(text):
        out[m.group(1)] = m.group(2).strip()
    return out


def format_rating_entry(status: str, source: str, notes: str, scores: dict) -> str:
    """Emit one rating entry as JS literal text (no surrounding `"<fid>": {...}`).

    Caller wraps with the key + braces in write_owner_ratings_file.
    Returns a multi-line string with 4-space indentation per the convention.
    """
    lines = []
    lines.append(f'    status: "{status}",')
    safe_source = source.replace('"', '\\"')
    lines.append(f'    source: "{safe_source}",')
    if notes:
        safe_notes = notes.replace('"', '\\"').replace("\n", " ")
        lines.append(f'    notes: "{safe_notes}",')
    if scores:
        lines.append("    scores: {")
        keys = [k for k in VALID_SCORE_KEYS if k in scores]
        for k in keys:
            v = int(scores[k]) if isinstance(scores[k], (int, float)) else 0
            lines.append(f"      {k}: {v},")
        lines.append("    }")
    return "\n".join(lines)


def write_owner_ratings_file(entries: Dict[str, str], path: str) -> None:
    """Atomic write of the full JS literal file from `{fid: entry_block}`.

    Sorts entries by fid for stable diffs. Uses temp + rename for atomicity.
    """
    out = [
        "// ============================================================",
        "// PAINT-BOOTH-0-PICKER-OWNER-RATINGS.JS",
        "// ============================================================",
        "// Purpose:",
        "//   Sparse owner/auditor override layer for picker rankings.",
        "//   Edited via /api/owner-rating (SPB-89).",
        "// ============================================================",
        "const PICKER_OWNER_RATINGS = {",
    ]
    for fid in sorted(entries.keys()):
        out.append(f'  "{fid}": {{')
        block = entries[fid].rstrip()
        if block and not block.startswith("    "):
            block = "\n".join(
                "    " + line.lstrip() if line.strip() else line
                for line in block.split("\n")
            )
        out.append(block)
        out.append("  },")
    out.append("};")
    out.append("")
    out.append("if (typeof window !== 'undefined') window.PICKER_OWNER_RATINGS = PICKER_OWNER_RATINGS;")
    out.append("")
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    os.replace(tmp_path, path)
