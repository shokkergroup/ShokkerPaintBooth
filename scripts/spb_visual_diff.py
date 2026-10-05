"""
scripts/spb_visual_diff.py - VISUAL-DIFF REVIEW HARNESS (audit TEST-06)
======================================================================

PURPOSE
-------
A finish-neutral *review* tool. After you (or Codex) edit finish/base/pattern
render code, run this to SEE what visibly changed. It renders a curated set of
finishes at a fixed size and fixed seed through the real engine, then diffs each
one against a committed baseline PNG. It produces an HTML report with:
  * a per-CATEGORY CONTACT SHEET (every finish, grouped by category, so the
    owner can scan a whole category at a glance), and
  * a side-by-side baseline-vs-current diff view for anything that
    changed / was added / was removed.

This is NOT a pass/fail gate. It NEVER fails the build - it always exits 0 and
just reports. The baselines are "golden images" that are refreshed *intentionally*
by the owner when a render change is accepted (see --update-baselines).

The curated set is BROAD-BUT-SAMPLED so a run stays a couple of minutes:
  * a representative slice of bases spanning the whole base catalog,
  * ONE representative per pattern CATEGORY/GROUP (the owner-reviewable
    PATTERN_GROUPS taxonomy in paint-booth-0-finish-data.js) so every pattern
    category is covered (Abstract/Fractal, Tech/Carbon, Geometry/Op-Art,
    Nature/Animals, Cultural/Dark, Decades, Skate/Surf, Reactive Accents),
  * ONE representative per monolithic FAMILY (grad_, cs_, cx_, spectrum_,
    prizm_, chameleon_, ... - sampled, never all 1000+ monolithics),
  * PLUS the masterclass cultural references registered in engine/registry.py:
    Viva Mexico (vm_*), Union Jacked (uj_*), Rising Sun (rs_*), Forbidden
    Dragon (fd_*), Mortal Shokk (ms_*), Grunge & Fun (gf_*), Guest Designers
    (gd_*).

The set is derived *dynamically* from the live registries + the live pattern
group taxonomy (read-only parse of paint-booth-0-finish-data.js, first-of-group)
so it stays valid even as IDs are added/removed - no hard-coded ID that can rot.
The exact resolved IDs are recorded in the baselines manifest.

HOW TO RUN
----------
    # Refresh / create baselines (owner does this on purpose after accepting
    # a render change). Writes PNGs + baselines_manifest.json:
    python scripts/spb_visual_diff.py --update-baselines

    # Default REVIEW mode: render current, compare to committed baselines,
    # write an HTML report (contact sheet + diff view) of what changed:
    python scripts/spb_visual_diff.py

    # Useful flags:
    python scripts/spb_visual_diff.py --size 256       # render size (default 256)
    python scripts/spb_visual_diff.py --seed 42        # fixed seed (default 42)
    python scripts/spb_visual_diff.py --limit 5        # cap finishes (quick smoke)
    python scripts/spb_visual_diff.py --only gloss,chrome   # explicit subset

OUTPUTS
-------
  scripts/../_visual_diff/baselines/*.png   committed golden images
  scripts/../_visual_diff/baselines_manifest.json   {id: {hash, w, h, kind, ...}}
  scripts/../_visual_diff/current/*.png      this-run renders (review mode)
  scripts/../_visual_diff/report.html        contact sheet + diff review report
  scripts/../_visual_diff/report.json        machine-readable diff summary

BASELINES ARE OWNER-OWNED
-------------------------
Baselines change ONLY when someone runs --update-baselines and commits the
result. A normal review run never touches the baseline PNGs. If the report shows
a finish changed and that change is intended/accepted, re-run with
--update-baselines to bless the new look. If it's a surprise, you just caught a
regression - investigate before refreshing.

This script creates NEW files only. It imports the engine exactly the way the
tests in tests/ do (sys.path -> project root, then `import shokker_engine_v2`
and `from engine.registry import ...`). It does not modify any render code.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import html
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# --------------------------------------------------------------------------
# Pathing: this file lives in scripts/, project root is one level up. Mirror
# the tests/conftest.py convention so `import shokker_engine_v2` resolves to the
# ROOT copy (tests resolve imports from root, and so must we).
# --------------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "_visual_diff"
BASELINE_DIR = OUT_DIR / "baselines"
CURRENT_DIR = OUT_DIR / "current"
MANIFEST_PATH = OUT_DIR / "baselines_manifest.json"
REPORT_HTML = OUT_DIR / "report.html"
REPORT_JSON = OUT_DIR / "report.json"

DEFAULT_SIZE = 256
DEFAULT_SEED = 42

# Owner-reviewable pattern taxonomy lives here (read-only). We parse the
# `const PATTERN_GROUPS = { ... }` object out of this file to pick one
# representative per pattern category. This is the single source of truth for
# pattern grouping in the picker - reading it keeps us in sync automatically.
PATTERN_DATA_JS = REPO / "paint-booth-0-finish-data.js"

# --------------------------------------------------------------------------
# Curated-set tuning. The goal is BROAD category coverage at a REASONABLE
# runtime: at least one representative from every base group, every pattern
# category, and every monolithic family - sampled, never exhaustive.
# --------------------------------------------------------------------------

# Representative regular bases (well-known, stable, simple to eyeball). These
# are always pinned first; the rest of the base catalog is sampled around them.
PREFERRED_BASES = [
    "gloss", "matte", "chrome", "satin", "flat_black",
    "brushed_aluminum", "carbon_weave",
]
# How many ADDITIONAL bases to sample evenly across the full sorted base list
# (on top of the pinned PREFERRED_BASES) so every region of the catalog shows.
BASE_SAMPLE_TARGET = 18

# Cap on representatives drawn per pattern category. One per category gives
# full category breadth without exploding the runtime.
PATTERN_REPS_PER_CATEGORY = 1

# Monolithic families we ALWAYS want pinned first (the headline effect groups),
# in this order. Every OTHER family present in the registry is still covered -
# this list only controls ordering / guarantees these lead.
MONO_PRIORITY_FAMILIES = [
    "grad", "cs", "cx", "spectrum", "prizm", "chameleon",
    "ghost", "depth", "reactive", "sparkle", "wave", "halo",
    "fractal", "exotic", "living", "aurora", "neon", "paradigm",
    "thermal", "iridescent", "spectral", "efx",
]
# Cultural / masterclass families, keyed by the ACTUAL monolithic id prefix
# (verified against the live MONOLITHIC_REGISTRY). We take ONE representative
# from each so the set stays small but ALWAYS anchors the cultural masterclasses.
# The values are just the human-friendly label used in the report.
MASTERCLASS_FAMILIES = {
    "vm": "Viva Mexico",        # vm_*  (engine.paint_v2.cultural_viva_mexico)
    "uj": "Union Jacked",       # uj_*  (engine.paint_v2.cultural_union_jacked)
    "rs": "Rising Sun",         # rs_*  (engine.paint_v2.cultural_rising_sun)
    "fd": "Forbidden Dragon",   # fd_*  (engine.paint_v2.cultural_forbidden_dragon)
    "ms": "Mortal Shokk",       # ms_*  (engine.paint_v2.cultural_mortal_shokk)
    "gf": "Grunge & Fun",       # gf_*  (engine.paint_v2.cultural_grunge_fun)
    "gd": "Guest Designers",    # gd_*  (engine.paint_v2.guest_designers)
}
# Minimum members for a monolithic prefix to count as a real "family" worth a
# representative. Singletons that are NOT cultural are skipped to keep the set
# tight (they are typically one-off legacy IDs).
MONO_FAMILY_MIN_MEMBERS = 2


@contextlib.contextmanager
def _suppress_stdout():
    """Engine import + render are very chatty on stdout. Mute during renders so
    our own progress lines stay readable. stderr is left alone."""
    saved = sys.stdout
    try:
        sys.stdout = io.StringIO()
        yield
    finally:
        sys.stdout = saved


def _family_of(finish_id):
    """First underscore-segment of an id, used as the monolithic family key."""
    return finish_id.split("_", 1)[0]


def _first_under_prefix(keys_sorted, prefix):
    """First key whose first underscore-segment equals `prefix`."""
    for k in keys_sorted:
        if _family_of(k) == prefix:
            return k
    return None


def _evenly_sample(items, count):
    """Pick `count` items spread evenly across `items` (preserves order).

    Deterministic. If count >= len(items) returns a copy of items. count<=0
    returns []. Used to sample the base catalog so every region is represented
    without rendering all of it.
    """
    n = len(items)
    if count <= 0 or n == 0:
        return []
    if count >= n:
        return list(items)
    # Evenly spaced indices across [0, n-1].
    step = (n - 1) / float(count - 1) if count > 1 else 0.0
    idxs = sorted({int(round(i * step)) for i in range(count)})
    # Rounding collisions can drop a couple; backfill from the front.
    out = [items[i] for i in idxs]
    if len(out) < count:
        for it in items:
            if it not in out:
                out.append(it)
                if len(out) >= count:
                    break
    return out


def load_pattern_groups():
    """Parse `const PATTERN_GROUPS = { ... }` from paint-booth-0-finish-data.js.

    Returns an ordered dict {group_label: [pattern_id, ...]} or None if the file
    is missing / unparseable. This is a READ-ONLY parse of the picker's pattern
    taxonomy - it never writes or mutates anything. Group labels in the source
    carry leading emoji glyphs; we keep them as-is for display.
    """
    import re
    from collections import OrderedDict

    try:
        txt = PATTERN_DATA_JS.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    start = txt.find("const PATTERN_GROUPS")
    if start == -1:
        return None
    end = txt.find("\n};", start)
    if end == -1:
        return None
    block = txt[start:end + 3]

    groups = OrderedDict()
    # Match  "Group Label": [ "id1", "id2", ... ]
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"\s*:\s*\[([^\]]*)\]', block):
        raw_name = m.group(1)
        ids = re.findall(r'"([^"]+)"', m.group(2))
        if not ids:
            continue
        # Decode any \uXXXX escapes in the label so emoji/symbols render.
        # unicode_escape turns "🌿" into a lone surrogate PAIR; we
        # recombine them into the real code point via utf-16/surrogatepass so
        # the label is valid UTF-8 (lone surrogates can't be UTF-8 encoded).
        name = raw_name
        if "\\u" in raw_name:
            try:
                decoded = raw_name.encode("utf-8").decode("unicode_escape")
                name = (decoded.encode("utf-16", "surrogatepass")
                               .decode("utf-16"))
            except Exception:
                name = raw_name
        groups[name] = ids
    return groups or None


def build_curated_set(base_reg, pattern_reg, mono_reg, pattern_groups=None):
    """Return an ordered list of (finish_id, kind, label, category) tuples.

    kind is one of 'base' | 'pattern' | 'monolithic'. category is a human label
    used to GROUP finishes in the contact sheet (e.g. 'Bases', 'Geometric',
    'mono: spectrum', 'Masterclass: Viva Mexico').

    The result is deterministic (sorted inputs, fixed preference order) so the
    curated set is stable run-to-run. Masterclass references are always included
    if present. Coverage:
      * Bases  -> pinned preferred + an even sample of the whole base catalog.
      * Patterns -> one representative per pattern GROUP (the owner-reviewable
        PATTERN_GROUPS taxonomy) that resolves to a live PATTERN_REGISTRY id, so
        every pattern category/group is covered.
      * Monolithics -> one representative per FAMILY prefix (priority families
        first, then the rest), plus cultural/masterclass families pinned.
    """
    base_keys = sorted(base_reg.keys())
    pattern_keys = sorted(pattern_reg.keys())
    mono_keys = sorted(mono_reg.keys())
    pattern_set = set(pattern_keys)

    curated: list[tuple[str, str, str, str]] = []
    seen: set[str] = set()

    def add(fid, kind, label, category):
        if fid and fid not in seen:
            curated.append((fid, kind, label, category))
            seen.add(fid)

    # ---- Bases: pinned preferred + even sample across the whole catalog. ----
    for bid in PREFERRED_BASES:
        if bid in base_reg:
            add(bid, "base", f"base / {bid}", "Bases")
    remaining_bases = [b for b in base_keys if b not in seen]
    for bid in _evenly_sample(remaining_bases, BASE_SAMPLE_TARGET):
        add(bid, "base", f"base / {bid}", "Bases")

    # ---- Patterns: one representative per pattern group (taxonomy order). ----
    if pattern_groups:
        for grp_name, ids in pattern_groups.items():
            # Preserve taxonomy order within the group (first resolvable id wins)
            # so the representative is stable and meaningful, not alphabetical.
            present = [i for i in ids if i in pattern_set]
            if not present:
                # Group whose IDs aren't in the live render registry (e.g. all
                # image-only / not yet wired). Skip cleanly.
                continue
            cat = f"Patterns: {grp_name}"
            for pid in present[:PATTERN_REPS_PER_CATEGORY]:
                add(pid, "pattern", f"pattern / {pid}", cat)
    else:
        # Fallback: no taxonomy available -> first few sorted NAMED patterns
        # (skip pure-numeric image ids so the fallback is still recognisable).
        added = 0
        for pid in pattern_keys:
            if pid and pid != "none" and not pid[0].isdigit():
                add(pid, "pattern", f"pattern / {pid}", "Patterns")
                added += 1
                if added >= 8:
                    break

    # ---- Monolithics: one representative per family (priority first). ----
    from collections import defaultdict
    fams: dict[str, list[str]] = defaultdict(list)
    for k in mono_keys:
        fams[_family_of(k)].append(k)

    def add_family(prefix, category_prefix="mono"):
        members = fams.get(prefix)
        if not members:
            return
        rep = sorted(members)[0]
        add(rep, "monolithic", f"mono:{prefix}_* / {rep}",
            f"{category_prefix}: {prefix}")

    # Priority families lead (stable, recognisable order).
    for prefix in MONO_PRIORITY_FAMILIES:
        add_family(prefix)
    # Then every remaining real family (>= MONO_FAMILY_MIN_MEMBERS) so coverage
    # is complete, sorted for determinism. Cultural families are pinned after.
    cultural = set(MASTERCLASS_FAMILIES.keys())
    for prefix in sorted(fams.keys()):
        if prefix in cultural:
            continue
        if len(fams[prefix]) < MONO_FAMILY_MIN_MEMBERS:
            continue
        add_family(prefix)

    # ---- Masterclass / cultural references (always anchored, pinned last). ----
    for prefix, nice in MASTERCLASS_FAMILIES.items():
        rep = _first_under_prefix(mono_keys, prefix)
        if rep:
            add(rep, "monolithic", f"masterclass:{nice} / {rep}",
                f"Masterclass: {nice}")

    return curated


def _make_zone(finish_id, kind, default_base="gloss"):
    """Build a single full-canvas zone for the given finish (mirrors the
    in-app/thumbnail convention)."""
    if kind == "base":
        return {
            "name": f"vd-{finish_id}", "color": "remaining",
            "base": finish_id, "pattern": "none", "intensity": "100",
        }
    if kind == "pattern":
        return {
            "name": f"vd-{finish_id}", "color": "remaining",
            "base": default_base, "pattern": finish_id, "intensity": "100",
        }
    # monolithic
    zone = {
        "name": f"vd-{finish_id}", "color": "remaining",
        "finish": finish_id, "intensity": "100",
    }
    try:
        from finish_colors_lookup import get_finish_colors
        fc = get_finish_colors(finish_id)
        if fc:
            zone["finish_colors"] = fc
    except Exception:
        pass
    return zone


def _png_bytes(rgb_uint8, size):
    """Encode an HxWx3 uint8 array to deterministic PNG bytes (resized to
    size x size if needed). Returns (bytes, (w, h))."""
    from PIL import Image
    import numpy as np

    arr = np.asarray(rgb_uint8)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    if arr.shape[2] == 4:
        arr = arr[:, :, :3]
    img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
    if img.size != (size, size):
        img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    # No timestamp chunk -> stable bytes for the same pixels.
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue(), img.size


def _hash_bytes(b):
    return hashlib.sha256(b).hexdigest()[:16]


def _safe_name(finish_id, kind):
    """Filesystem-safe, collision-proof basename for a finish PNG.

    The `kind` prefix matters on case-insensitive filesystems (Windows): the
    base `carbon_weave` and the pattern `Carbon_Weave` would otherwise map to
    the same file and clobber each other. Prefixing by kind keeps them distinct.
    """
    raw = f"{kind}__{finish_id}"
    return (raw.replace("/", "_").replace("\\", "_").replace(":", "_")
            .replace(" ", "_"))


def _mean_abs_diff(png_a_path, png_b_bytes):
    """Mean absolute per-pixel difference (0..255) between a baseline PNG on
    disk and current PNG bytes. Returns None if shapes mismatch or read fails."""
    from PIL import Image
    import numpy as np

    try:
        a = np.asarray(Image.open(png_a_path).convert("RGB"), dtype=np.float32)
        b = np.asarray(Image.open(io.BytesIO(png_b_bytes)).convert("RGB"),
                       dtype=np.float32)
    except Exception:
        return None
    if a.shape != b.shape:
        return None
    return float(np.abs(a - b).mean())


def _load_engine():
    """Import the engine the same way tests do; wire V5 registries onto the
    legacy module so build_multi_zone sees the full catalog. Returns
    (build_multi_zone, BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY,
     PATTERN_GROUPS)."""
    with _suppress_stdout():
        from engine.registry import (
            BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY,
        )
        # Pattern group taxonomy (used to pick one rep per category). Best
        # effort: read-only parse of the picker data; if absent we fall back to
        # first-few-sorted named patterns.
        pattern_groups = load_pattern_groups()
        import shokker_engine_v2 as _legacy
        _legacy.BASE_REGISTRY = BASE_REGISTRY
        _legacy.PATTERN_REGISTRY = PATTERN_REGISTRY
        _legacy.MONOLITHIC_REGISTRY = MONOLITHIC_REGISTRY
        build_multi_zone = _legacy.build_multi_zone
    return (build_multi_zone, BASE_REGISTRY, PATTERN_REGISTRY,
            MONOLITHIC_REGISTRY, pattern_groups)


def render_finish(build_multi_zone, src_png, out_dir, finish_id, kind, size, seed):
    """Render one finish to an HxWx3 uint8 array via the real pipeline."""
    zone = _make_zone(finish_id, kind)
    with _suppress_stdout():
        paint_rgb, _spec, _meta = build_multi_zone(
            str(src_png), str(out_dir), [zone],
            iracing_id="23371", seed=seed, save_debug_images=False,
        )
    return paint_rgb


# --------------------------------------------------------------------------
# HTML report
# --------------------------------------------------------------------------
_HTML_HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SPB Visual Diff Review</title>
<style>
 body{{font-family:system-ui,Segoe UI,Arial,sans-serif;background:#14161a;color:#e8eaed;margin:0;padding:24px}}
 h1{{font-size:20px;margin:0 0 4px}}
 h2{{font-size:16px;margin:26px 0 10px;border-bottom:1px solid #2a2e35;padding-bottom:6px}}
 .sub{{color:#9aa0a6;font-size:13px;margin-bottom:20px}}
 .legend{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:18px;font-size:13px}}
 .pill{{padding:3px 10px;border-radius:999px;font-weight:600}}
 .changed{{background:#5a3a00;color:#ffd98a}}
 .added{{background:#0d4429;color:#9ff0c4}}
 .removed{{background:#4a1414;color:#ffb4b4}}
 .same{{background:#23262b;color:#9aa0a6}}
 .error{{background:#4a1414;color:#ffb4b4}}
 table{{border-collapse:collapse;width:100%}}
 td,th{{border-bottom:1px solid #2a2e35;padding:10px;vertical-align:top;text-align:left}}
 th{{color:#9aa0a6;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
 .imgs{{display:flex;gap:10px}}
 .imgs figure{{margin:0;text-align:center}}
 .imgs img{{width:160px;height:160px;image-rendering:auto;border:1px solid #2a2e35;border-radius:6px;background:#0b0c0e}}
 .imgs figcaption{{font-size:11px;color:#9aa0a6;margin-top:4px}}
 .metric{{font-variant-numeric:tabular-nums}}
 code{{background:#23262b;padding:1px 5px;border-radius:4px;font-size:12px}}
 .note{{margin-top:24px;color:#9aa0a6;font-size:12px;max-width:760px;line-height:1.5}}
 /* Contact sheet */
 .toc{{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 4px;font-size:12px}}
 .toc a{{color:#9ff0c4;text-decoration:none;background:#1b2430;padding:3px 9px;border-radius:999px;border:1px solid #243140}}
 .toc a:hover{{background:#243140}}
 .sheet{{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:12px;margin-bottom:6px}}
 .cell{{text-align:center;font-size:11px;color:#c3c7cc}}
 .cell img{{width:128px;height:128px;border:1px solid #2a2e35;border-radius:6px;background:#0b0c0e;display:block;margin:0 auto 4px}}
 .cell .fid{{display:block;word-break:break-all;line-height:1.25}}
 .cell.changed-cell img{{border-color:#caa14a;box-shadow:0 0 0 2px #5a3a00}}
 .cell.added-cell img{{border-color:#3ea877;box-shadow:0 0 0 2px #0d4429}}
 .badge{{display:inline-block;font-size:9px;font-weight:700;padding:1px 5px;border-radius:6px;margin-top:2px;text-transform:uppercase;letter-spacing:.03em}}
 .cat-count{{color:#6f757d;font-weight:400;font-size:12px;text-transform:none;letter-spacing:0}}
</style></head><body>
<h1>SPB Visual Diff Review</h1>
<div class="sub">{sub}</div>
"""


def _img_tag(rel, cls="", size=160):
    if rel:
        c = f' class="{cls}"' if cls else ""
        return f'<img{c} src="{html.escape(rel)}" alt="">'
    return (
        f'<div style="width:{size}px;height:{size}px;border:1px dashed #3a3e45;'
        'border-radius:6px;display:flex;align-items:center;justify-content:center;'
        'color:#5f656d;font-size:12px">none</div>'
    )


def _anchor(cat):
    return "cat_" + "".join(c if c.isalnum() else "_" for c in cat)


def _render_contact_sheet(rows):
    """Build the per-category contact sheet HTML.

    Groups EVERY rendered finish by its category, so the owner can scan a whole
    category at a glance. Cells link to the current render (review mode) or the
    baseline (update mode); changed/added cells get a coloured highlight.
    """
    from collections import OrderedDict

    # Preserve curated order: first time we see a category, record it.
    by_cat = OrderedDict()
    for r in rows:
        if r.get("status") == "removed":
            # Removed finishes have no current/baseline render to show here.
            continue
        cat = r.get("category") or "Uncategorised"
        by_cat.setdefault(cat, []).append(r)

    if not by_cat:
        return ""

    parts = ['<h2>Contact sheet <span class="cat-count">'
             f'({len(by_cat)} categories)</span></h2>']

    # Table of contents (jump links).
    parts.append('<div class="toc">')
    for cat in by_cat:
        parts.append(f'<a href="#{_anchor(cat)}">{html.escape(cat)} '
                     f'({len(by_cat[cat])})</a>')
    parts.append('</div>')

    for cat, items in by_cat.items():
        parts.append(f'<h2 id="{_anchor(cat)}">{html.escape(cat)} '
                     f'<span class="cat-count">({len(items)})</span></h2>')
        parts.append('<div class="sheet">')
        for r in items:
            # Prefer the current render; fall back to baseline (update mode).
            rel = r.get("current_rel") or r.get("baseline_rel")
            status = r.get("status", "")
            cell_cls = "cell"
            badge = ""
            if status == "changed":
                cell_cls += " changed-cell"
                badge = '<span class="badge changed">changed</span>'
            elif status == "added":
                cell_cls += " added-cell"
                badge = '<span class="badge added">added</span>'
            elif status == "error":
                badge = '<span class="badge error">error</span>'
            img = _img_tag(rel, size=128)
            parts.append(
                f'<div class="{cell_cls}">{img}'
                f'<span class="fid">{html.escape(r["id"])}</span>{badge}</div>'
            )
        parts.append('</div>')
    return "".join(parts)


def write_html_report(rows, summary, size, seed, generated):
    counts = summary["counts"]
    sub = (
        f"Rendered {summary['rendered']} finishes across "
        f"{summary.get('categories', '?')} categories at {size}&times;{size}, "
        f"seed {seed} &mdash; {generated}. "
        f"<strong>Review only</strong>: this never fails the build. "
        f"Baselines are refreshed intentionally via "
        f"<code>--update-baselines</code>."
    )
    parts = [_HTML_HEAD.format(sub=sub)]
    parts.append(
        '<div class="legend">'
        f'<span class="pill changed">changed {counts["changed"]}</span>'
        f'<span class="pill added">added {counts["added"]}</span>'
        f'<span class="pill removed">removed {counts["removed"]}</span>'
        f'<span class="pill same">unchanged {counts["same"]}</span>'
        f'<span class="pill error">error {counts.get("error", 0)}</span>'
        '</div>'
    )

    # ---- Diff view (changed / added / removed) ----
    changed_rows = [r for r in rows if r["status"] in ("changed", "added", "removed")]
    parts.append('<h2>Changes vs committed baselines</h2>')
    if not changed_rows:
        parts.append(
            '<p style="color:#9ff0c4">No visible changes vs committed '
            'baselines. Nothing to review.</p>'
        )
    else:
        parts.append("<table><thead><tr>"
                     "<th>Status</th><th>Finish</th><th>Mean abs diff</th>"
                     "<th>Baseline vs Current</th></tr></thead><tbody>")
        for r in changed_rows:
            mad = r.get("mean_abs_diff")
            mad_txt = "&mdash;" if mad is None else f"{mad:.2f}"
            base_img = _img_tag(r.get("baseline_rel"))
            cur_img = _img_tag(r.get("current_rel"))
            parts.append(
                "<tr>"
                f'<td><span class="pill {r["status"]}">{r["status"]}</span></td>'
                f'<td><code>{html.escape(r["id"])}</code><br>'
                f'<span style="color:#9aa0a6;font-size:11px">'
                f'{html.escape(r.get("label", ""))}</span></td>'
                f'<td class="metric">{mad_txt}</td>'
                '<td><div class="imgs">'
                f'<figure>{base_img}<figcaption>baseline</figcaption></figure>'
                f'<figure>{cur_img}<figcaption>current</figcaption></figure>'
                '</div></td>'
                "</tr>"
            )
        parts.append("</tbody></table>")

    # ---- Per-category contact sheet ----
    parts.append(_render_contact_sheet(rows))

    parts.append(
        '<p class="note">This is a review tool, not a gate. A finish showing '
        'up as <em>changed</em> just means its pixels differ from the committed '
        'golden image &mdash; that may be an intended improvement or an '
        'accidental regression. The contact sheet above shows every rendered '
        'finish grouped by category so you can scan a whole category at a '
        'glance. If a change is intended, bless it by running '
        '<code>python scripts/spb_visual_diff.py --update-baselines</code> and '
        'committing the refreshed baselines. Baselines are owner-owned and are '
        'never modified by a plain review run.</p>'
    )
    parts.append("</body></html>")
    # errors="replace" is belt-and-suspenders: a stray lone surrogate in any
    # label must never crash this never-fail review tool.
    REPORT_HTML.write_text("".join(parts), encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------
def run(update_baselines, size, seed, limit, only):
    import numpy as np
    from PIL import Image

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[visual-diff] loading engine (root={REPO}) ...")
    (build_multi_zone, base_reg, pattern_reg, mono_reg,
     pattern_groups) = _load_engine()
    print(f"[visual-diff] registries: {len(base_reg)} bases, "
          f"{len(pattern_reg)} patterns, {len(mono_reg)} monolithics, "
          f"{0 if not pattern_groups else len(pattern_groups)} "
          f"pattern groups")

    curated = build_curated_set(base_reg, pattern_reg, mono_reg,
                                pattern_groups)
    if only:
        only_set = {x.strip() for x in only.split(",") if x.strip()}
        curated = [c for c in curated if c[0] in only_set]
    if limit and limit > 0:
        curated = curated[:limit]
    n_categories = len({c[3] for c in curated})
    print(f"[visual-diff] curated set: {len(curated)} finishes "
          f"across {n_categories} categories")

    mode = "UPDATE-BASELINES" if update_baselines else "REVIEW"
    print(f"[visual-diff] mode: {mode}  size={size}  seed={seed}")

    # Load previous baseline manifest (for review mode + removed detection).
    prev_manifest = {}
    if MANIFEST_PATH.exists():
        try:
            prev_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            prev_manifest = {}
    prev_finishes = prev_manifest.get("finishes", {})

    if not update_baselines:
        CURRENT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    new_manifest_finishes = {}
    rendered = 0
    failed = 0
    t_start = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="spb_vdiff_") as tmp:
        tmp = Path(tmp)
        # Be robust if tempfile.mkdtemp was monkeypatched (e.g. the test
        # harness redirects it to a fixed path that may not exist yet).
        tmp.mkdir(parents=True, exist_ok=True)
        src_png = tmp / "src.png"
        gray = np.full((size, size, 3), 0x88, dtype=np.uint8)
        Image.fromarray(gray).save(src_png)
        out_dir = tmp / "out"
        out_dir.mkdir(parents=True, exist_ok=True)

        for i, (fid, kind, label, category) in enumerate(curated, 1):
            t0 = time.perf_counter()
            try:
                paint_rgb = render_finish(
                    build_multi_zone, src_png, out_dir, fid, kind, size, seed)
                png, dims = _png_bytes(paint_rgb, size)
            except Exception as exc:
                failed += 1
                print(f"  [{i:3d}/{len(curated)}] FAIL {kind}/{fid}: {exc!r}")
                rows.append({
                    "id": fid, "kind": kind, "label": label,
                    "category": category, "status": "error", "error": str(exc),
                })
                continue

            dt_ms = (time.perf_counter() - t0) * 1000.0
            cur_hash = _hash_bytes(png)
            rendered += 1

            safe = _safe_name(fid, kind)
            baseline_png = BASELINE_DIR / f"{safe}.png"

            if update_baselines:
                baseline_png.write_bytes(png)
                new_manifest_finishes[fid] = {
                    "kind": kind, "label": label, "category": category,
                    "file": f"baselines/{safe}.png",
                    "hash": cur_hash, "w": dims[0], "h": dims[1],
                }
                # In update mode the report contact sheet shows the baseline.
                rows.append({
                    "id": fid, "kind": kind, "label": label,
                    "category": category, "status": "baselined",
                    "baseline_rel": f"baselines/{safe}.png",
                })
                print(f"  [{i:3d}/{len(curated)}] baselined {kind}/{fid} "
                      f"({dt_ms:5.0f}ms)")
                continue

            # REVIEW mode -> write current render + compare.
            current_png = CURRENT_DIR / f"{safe}.png"
            current_png.write_bytes(png)
            prev = prev_finishes.get(fid)
            if prev is None or not baseline_png.exists():
                status = "added"
                mad = None
            else:
                if prev.get("hash") == cur_hash:
                    status = "same"
                    mad = 0.0
                else:
                    status = "changed"
                    mad = _mean_abs_diff(baseline_png, png)
                    # Hash differs but pixels identical (rare) -> treat as same.
                    if mad is not None and mad == 0.0:
                        status = "same"
            row = {
                "id": fid, "kind": kind, "label": label, "category": category,
                "status": status, "mean_abs_diff": mad,
                "render_ms": round(dt_ms, 1),
                "current_rel": f"current/{safe}.png",
            }
            if baseline_png.exists():
                row["baseline_rel"] = f"baselines/{safe}.png"
            rows.append(row)
            flag = "" if status == "same" else "  <<<"
            print(f"  [{i:3d}/{len(curated)}] {status:7s} {kind}/{fid}"
                  f"  mad={('-' if mad is None else f'{mad:.2f}')}{flag}")

    elapsed = time.perf_counter() - t_start

    if update_baselines:
        manifest = {
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "size": size, "seed": seed,
            "count": len(new_manifest_finishes),
            "categories": len({v["category"] for v in
                               new_manifest_finishes.values()}),
            "finishes": new_manifest_finishes,
        }
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # Write a report (contact sheet of the freshly-baselined set) so the
        # owner can eyeball what was just blessed.
        summary = {
            "generated": manifest["generated"], "size": size, "seed": seed,
            "rendered": rendered, "failed": failed,
            "elapsed_s": round(elapsed, 1),
            "categories": manifest["categories"],
            "counts": {"changed": 0, "added": 0, "removed": 0,
                       "same": rendered, "error": failed},
        }
        write_html_report(rows, summary, size, seed, manifest["generated"])
        print(f"[visual-diff] wrote {len(new_manifest_finishes)} baselines "
              f"across {manifest['categories']} categories "
              f"+ manifest in {elapsed:.1f}s")
        print(f"  -> {MANIFEST_PATH}")
        print(f"  -> {REPORT_HTML}")
        print("[visual-diff] baselines refreshed. Commit _visual_diff/ to bless.")
        return 0

    # REVIEW mode: detect removed finishes (in baseline manifest, not rendered).
    rendered_ids = {r["id"] for r in rows}
    for fid, prev in prev_finishes.items():
        if fid not in rendered_ids:
            safe = _safe_name(fid, prev.get("kind", "?"))
            baseline_png = BASELINE_DIR / f"{safe}.png"
            row = {
                "id": fid, "kind": prev.get("kind", "?"),
                "label": prev.get("label", ""),
                "category": prev.get("category", "Uncategorised"),
                "status": "removed", "mean_abs_diff": None,
            }
            if baseline_png.exists():
                row["baseline_rel"] = f"baselines/{safe}.png"
            rows.append(row)

    counts = {"changed": 0, "added": 0, "removed": 0, "same": 0, "error": 0}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "size": size, "seed": seed, "rendered": rendered, "failed": failed,
        "elapsed_s": round(elapsed, 1), "counts": counts,
        "categories": len({r["category"] for r in rows
                           if r.get("status") != "removed"}),
        "baseline_manifest": str(MANIFEST_PATH.name),
        "have_baselines": bool(prev_finishes),
    }
    report = {"summary": summary, "finishes": rows}
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_html_report(rows, summary, size, seed, summary["generated"])

    if not prev_finishes:
        print("[visual-diff] NOTE: no committed baselines found. Everything is "
              "reported as 'added'. Run --update-baselines to create them.")
    print(f"[visual-diff] review done in {elapsed:.1f}s: "
          f"changed={counts['changed']} added={counts['added']} "
          f"removed={counts['removed']} same={counts['same']} "
          f"failed={failed}")
    print(f"  -> {REPORT_HTML}")
    print(f"  -> {REPORT_JSON}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="SPB visual-diff review harness (finish-neutral, never fails)."
    )
    ap.add_argument("--update-baselines", action="store_true",
                    help="Write/refresh baseline PNGs + manifest (owner action).")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE,
                    help=f"Render size square (default {DEFAULT_SIZE}).")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help=f"Fixed render seed (default {DEFAULT_SEED}).")
    ap.add_argument("--limit", type=int, default=0,
                    help="Cap number of finishes (0 = all curated).")
    ap.add_argument("--only", default="",
                    help="Comma-separated explicit subset of finish IDs.")
    args = ap.parse_args(argv)

    # Make our own progress prints Unicode-safe on Windows consoles.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        return run(args.update_baselines, args.size, args.seed,
                   args.limit, args.only)
    except Exception as exc:
        # REVIEW tool: never fail the build. Report and exit 0.
        import traceback
        print(f"[visual-diff] harness error (non-fatal): {exc!r}", file=sys.stderr)
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
