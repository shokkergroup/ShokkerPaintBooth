#!/usr/bin/env python3
"""
Build a self-contained editable HTML workbench for one (or many) categories.

The owner asked (tick 85): "put them on HTML editable pages. Make it like a
WORKBENCH file where EVERYTHING is in one HTML file per whatever category.
So it all stays together and I can see everything on one page."

Each generated page (SPB_WORKBENCH_<slug>.html) contains:
  * Every finish in that category: thumbnail, current scores, intent.
  * A note on WHAT (if anything) we changed in the engine for it.
  * Per-finish rating form (status + notes + scores).
  * Auto-save to localStorage so refresh doesn't lose work.
  * "Export" button → copy a paste-ready JS block for
    paint-booth-0-picker-owner-ratings.js, or POST to /api/owner-rating if
    a local server is running.
  * Header summary: M7 category mean / tier breakdown / quick links.

Index page (SPB_WORKBENCHES_INDEX.html) is also produced, linking to every
generated category workbench plus the master SPB_FINISH_QUALITY_WORKBOOK.html.

USAGE
-----
    # Build a single category
    python scripts/build_category_workbench.py --category "Enhanced Foundation"

    # Build the 6 priority categories from M7 STILL-WEAK list + recently-edited
    python scripts/build_category_workbench.py --priority

    # Build EVERY category (warning: writes ~120 HTML files)
    python scripts/build_category_workbench.py --all
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from html import escape
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

V5_ROOT = Path(__file__).resolve().parent.parent
SCORECARD = V5_ROOT / "paint-booth-0-catalog-scorecard.js"
RATINGS = V5_ROOT / "paint-booth-0-picker-owner-ratings.js"
M7_JSON = V5_ROOT / "_workbook_metrics" / "m7_composite.json"
M1_JSON = V5_ROOT / "_workbook_metrics" / "m1_sibling_diff.json"
OUT_DIR = V5_ROOT  # generate workbenches at project root for easy access


# Categories the owner cares about most after tick 85 metric fixes.
PRIORITY_CATEGORIES = [
    "★ Enhanced Foundation",   # foundation_enhanced.py edited tick 53 + enh_* micro tick 51
    "Ghost Geometry",               # M7 worst (real, spec_driven) — owner reviewed tick 88
    "Weather & Age",                # M7 worst (real, new cluster)
    "Abstract Art",                 # M7 worst (real, new cluster)
    "Weathered & Aged",             # weathered_worn.py edited (251 lines, owner_review_weathered_aged.py)
    "Weathering",                   # weathered_worn.py mostly lives here
    "Textile-Inspired",             # M7 worst (real)
    "Foundation",                   # M7 BEST after tick 80 — show as healthy baseline
    "Exotic Metal",                 # exotic_metal.py +51 lines
    "Candy & Pearl",                # candy_special.py +352 lines
    "Race Heritage",                # owner_review_racing_heritage.py +53 lines
    "Racing Heritage",              # same
    "Stone",                        # stone_textile.py +70 lines
]

# Owner tick-88 brief: FUSION LAB review queue (14 categories, ~143 finishes).
# Process in this order AFTER Ghost Geometry engineering completes (SPB-100).
FUSION_LAB_CATEGORIES = [
    "Depth Illusion",
    "Material Gradients",
    "Directional Grain",
    "Reactive Panels",
    "Sparkle Systems",
    "Sparkle",
    "Multi-Scale Texture",
    "Weather & Age",
    "Exotic Physics",
    "Tri-Zone Materials",
    "Metallic Halos",
    "Light Waves",
    "Fractal Chaos",
    "Spectral Reactive",
    "Panel Quilting",
]


# Per-category "what changed" notes. Used in the header of each workbench page.
CATEGORY_CHANGE_NOTES = {
    "★ Enhanced Foundation": (
        "Tick 53 (SPB-91): removed the multi_scale_noise grain pass from "
        "_subtle_grain in foundation_enhanced.py. Owner critique was "
        "\"All of the enhancements on the paint side of it was just flipping "
        "around diagonal lines.\" That was the coarse+fine grain at scales "
        "16/32/64 and 64/128. Kept warmth/cool/desat color shifts (mean-shift "
        "only, doctrine-compatible).\n"
        "Tick 51: added _spb_enh_micro_signature in shokker_engine_v2.py — "
        "6 keyword families (chrome, brushed, carbon, pearl, metallic, frozen) "
        "drive the micro-noise signature per finish name."
    ),
    "Weathered & Aged": (
        "Edits to owner_review_weathered_aged.py (+37 lines) and "
        "weathered_worn.py (+251 lines, significant rewrite). Net effect: "
        "more pronounced corrosion/patina detail vs the v6.0.x baseline. "
        "Specific tick-by-tick attribution would need git archaeology."
    ),
    "Weathering": (
        "weathered_worn.py +251 lines lives mostly here. Significant "
        "rewrite of the corrosion/oxide pipelines."
    ),
    "Exotic Metal": (
        "exotic_metal.py +51 lines. Engine module change; per-finish visual "
        "diff would need before/after probes."
    ),
    "Candy & Pearl": (
        "candy_special.py +352 lines — the largest single-file engine change "
        "in this loop. Visual review recommended on all 15 finishes."
    ),
    "Race Heritage": (
        "owner_review_racing_heritage.py +53 lines."
    ),
    "Racing Heritage": (
        "owner_review_racing_heritage.py +53 lines (same edits as Race Heritage)."
    ),
    "Stone": (
        "stone_textile.py +70 lines + SPB-87 reorder via "
        "_spb_reapply_stone_textile_overrides in shokker_engine_v2.py."
    ),
    # ------------------------------------------------------------------
    # FUSION LAB review queue — owner tick 88 brief (2026-05-16). All carry
    # the SPB-99 doctrine: 2048² = whole car (patterns ~20% current scale),
    # spec channels need micro chroma modulation (many shades, not one solid).
    # ------------------------------------------------------------------
    "Depth Illusion": (
        "OWNER NOTE (tick 88): \"already seeing WAY TOO BIG patterns again "
        "but now you know to fix/make them smaller. AND make the specs more "
        "enhanced.\"\nSPB-99 doctrine applies in full — shrink pattern scale "
        "to ~20%, add multi-shade spec channel modulation. Engineering pass "
        "after Ghost Geometry fixes land."
    ),
    "Material Gradients": (
        "OWNER QUEUED (tick 88) — pending fusion-lab review. Apply SPB-99 "
        "doctrine as starting point: patterns at car-body scale, multi-shade "
        "spec instead of single-color regions."
    ),
    "Directional Grain": (
        "OWNER QUEUED (tick 88). SPB-99 doctrine baseline. Likely needs "
        "finer grain pitch + chromatic micro-variation across grain lines."
    ),
    "Reactive Panels": (
        "OWNER QUEUED (tick 88). SPB-99 doctrine baseline."
    ),
    "Sparkle Systems": (
        "OWNER NOTE (tick 88): \"can tell you right now there are not "
        "NEARLY enough sparkles.\"\nAction: increase sparkle particle density "
        "significantly. Cross-reference Enhanced Foundation Exotic Stardust "
        "(tick 52) which uses 100k particles via density_per_megapixel=25000 "
        "as a high-density precedent."
    ),
    "Sparkle": (
        "OWNER NOTE (tick 88, implied from \"Sparkle System\" critique): "
        "not nearly enough sparkles. Apply same density treatment as Sparkle "
        "Systems."
    ),
    "Multi-Scale Texture": (
        "OWNER QUEUED (tick 88). SPB-99 doctrine baseline. Multi-scale is "
        "literally about scale variation — sanity-check that the smallest "
        "scale band actually shows up at car-body 2048²."
    ),
    "Exotic Physics": (
        "OWNER QUEUED (tick 88). SPB-99 doctrine baseline. Name implies "
        "extreme effects — owner critique will likely target whether the "
        "physics-themed finishes actually look as wild as the names suggest."
    ),
    "Tri-Zone Materials": (
        "OWNER QUEUED (tick 88). SPB-99 doctrine baseline."
    ),
    "Metallic Halos": (
        "OWNER VERDICT (tick 88): \"I HATE that category. I like metallic "
        "finishes so rework it into something badass and grungy. "
        "EDGY/COOL.\"\nCategory-level reject. Drop the soft halo aesthetic. "
        "Target: industrial, weathered metal vibe — scuffed, dented, painted-"
        "over chrome with hard contrast. Needs category redesign, not just "
        "per-finish tweaks."
    ),
    "Light Waves": (
        "OWNER NOTE (tick 88): \"needs to be much more dynamic.\"\nAction: "
        "increase wave amplitude variation, add cross-frequency interference, "
        "use multi-shade spec to make wave crests pop with chromatic richness "
        "(SPB-99 principle 2)."
    ),
    "Fractal Chaos": (
        "OWNER NOTE (tick 88): \"if we say chaos it SHOULD be chaos not "
        "what's there now.\"\nCurrent fractal renderers are too ordered. "
        "Action: increase iteration depth, randomize rotation/translation "
        "per fractal arm, break the visible self-similarity that makes it "
        "look algorithmic instead of chaotic."
    ),
    "Spectral Reactive": (
        "OWNER NOTE (tick 88): \"should REALLY push the boundaries but "
        "doesn't.\"\nAction: amplify the spectral shift effect — wider hue "
        "swings across reactive bands, sharper transitions, more visible "
        "spectrum readouts. SPB-99 principle 2 (multi-shade spec) is the "
        "natural lever."
    ),
    "Panel Quilting": (
        "OWNER QUEUED (tick 88). SPB-99 doctrine baseline — likely also "
        "needs smaller quilt cells given ghost_quilt was rejected for "
        "exactly that reason."
    ),
    "Ghost Geometry": (
        "No direct engine edits to ghost_* finishes. They appear in M7 "
        "STILL-WEAK because of intentional spec_driven flatness (paint is "
        "neutral, all detail is in the spec channel). The composite reflects "
        "low M2 (intent-fit vocabulary doesn't match flat output) and low M6 "
        "(category floor expectation tuned for full-intent finishes). "
        "Worth owner review: do these need a category-specific intent-fit "
        "model, or are they genuinely under-detailed?"
    ),
    "Weather & Age": (
        "OWNER QUEUED for fusion-lab review (tick 88). Already probed (tick 86, "
        "SPB-98): 10/10 finishes BAKE-STALE — renderers produce spec_M_std "
        "15-53 (substantial structure). Re-bake via SPB-96 will help. "
        "Owner review after rebake should confirm size + spec richness meet "
        "SPB-99 doctrine. Originally surfaced as 'real quality cluster' "
        "by SPB-97 color-aware M1; correct call now is bake-stale."
    ),
    "Abstract Art": (
        "No direct edits. abstract_* spec_pattern finishes — surfaced as a "
        "real-quality cluster (mean 38.3, 10/17 critical) after color-aware "
        "M1 in tick 85. Mostly spec_pattern surface, may need spec-richness "
        "boost or distinct visual identity per finish."
    ),
    "Weathered & Worn": (
        "Significant rewrite — weathered_worn.py +251 lines changed across "
        "the loop. Specific ticks need git-archaeology to enumerate; the "
        "net effect is more pronounced corrosion/patina detail vs the "
        "v6.0.x baseline."
    ),
    "Textile-Inspired": (
        "No direct paint_v2 edit to textile_silk_sheen etc. Textile lives "
        "in stone_textile.py (+70 lines, mostly SPB-87 reorder). The 6 "
        "textile_* finishes all rank critical — visual probe recommended."
    ),
    "Foundation": (
        "No edits to f_* paint code — Foundation is doctrinally flat (SPB-74 "
        "declined). After tick 80's intent-aware M7 fix, Foundation went "
        "from \"worst category by clone penalty\" to BEST (mean 95.1, 34/34 "
        "keepers). This page exists as a HEALTHY-BASELINE reference: compare "
        "the other categories' workbenches against this layout."
    ),
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_scorecard() -> dict[str, dict]:
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    body_match = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if body_match is None:
        raise ValueError(f"Could not parse scorecard JSON body from {SCORECARD}")
    body = re.sub(r"//[^\n]*", "", body_match.group(1))
    return json.loads(body)


def load_m7() -> dict:
    if not M7_JSON.exists():
        print(f"[warn] {M7_JSON} not found — run scripts/spb_workbook_compute_m7.py")
        return {"byFinish": {}, "byCategory": {}}
    return json.loads(M7_JSON.read_text(encoding="utf-8"))


def load_existing_ratings() -> dict[str, dict]:
    """Parse paint-booth-0-picker-owner-ratings.js to get existing ratings."""
    if not RATINGS.exists():
        return {}
    txt = RATINGS.read_text(encoding="utf-8", errors="replace")
    # Crude best-effort: find each `"key": { ... }` and grab the inner.
    out = {}
    for m in re.finditer(
        r'"((?:base|monolithic|pattern|spec_pattern):[a-z0-9_]+)"\s*:\s*\{((?:[^{}]|\{[^{}]*\})*)\}',
        txt, flags=re.S,
    ):
        fid = m.group(1)
        block = m.group(2)
        status = re.search(r'status\s*:\s*"([^"]+)"', block)
        notes = re.search(r'notes\s*:\s*"([^"]*)"', block)
        out[fid] = {
            "status": status.group(1) if status else "",
            "notes": notes.group(1) if notes else "",
        }
    return out


# ---------------------------------------------------------------------------
# Thumbnail discovery
# ---------------------------------------------------------------------------

def find_thumbnail(fid: str) -> str | None:
    """Return relative path to the thumbnail PNG for this fid, or None."""
    surface, _, stem = fid.partition(":")
    folder_map = {
        "base": "thumbnails/base",
        "monolithic": "thumbnails/monolithic",
        "pattern": "thumbnails/pattern",
        "spec_pattern": "thumbnails/spec_patterns",
    }
    folder = folder_map.get(surface)
    if not folder:
        return None
    # Try the standard path
    rel = f"{folder}/{stem}.png"
    if (V5_ROOT / rel).is_file():
        return rel
    # Try alt spec_pattern folders
    if surface == "spec_pattern":
        for alt in ("thumbnails/spec_patterns_metal", "thumbnails/spec_patterns_visual"):
            for suffix in ("", "_160"):
                p = f"{alt}/{stem}{suffix}.png"
                if (V5_ROOT / p).is_file():
                    return p
    return None


# ---------------------------------------------------------------------------
# Page generation
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").upper()
    return s or "UNKNOWN"


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SPB Workbench — {category}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
         margin: 0; background: #1a1a1a; color: #e0e0e0; }}
  header {{ position: sticky; top: 0; background: #0b0b0b; padding: 16px 24px;
           border-bottom: 1px solid #333; z-index: 10; }}
  header h1 {{ margin: 0 0 6px 0; font-size: 20px; }}
  header .meta {{ font-size: 13px; color: #888; }}
  header .changes {{ background: #1f2a1f; padding: 10px 14px; border-left: 4px solid #4a7c4a;
                    margin-top: 12px; white-space: pre-wrap; font-size: 13px;
                    color: #c8e0c8; max-width: 1100px; line-height: 1.4; }}
  header .actions {{ margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }}
  header button {{ background: #2a4a7c; color: #fff; border: 1px solid #4a6a9c;
                  padding: 8px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; }}
  header button:hover {{ background: #3a5a8c; }}
  header button.exp {{ background: #4a7c4a; }}
  header button.exp:hover {{ background: #5a8c5a; }}
  header a {{ color: #6ab0ff; }}
  main {{ padding: 16px 24px 80px 24px; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 1700px; }}
  th, td {{ border: 1px solid #2a2a2a; padding: 8px; vertical-align: top;
           font-size: 13px; }}
  th {{ background: #0f0f0f; color: #aaa; text-align: left; position: sticky;
        top: 134px; z-index: 5; }}
  tr:hover {{ background: #1e1e1e; }}
  td.thumb img {{ width: 144px; height: 144px; object-fit: cover; border: 1px solid #333;
                 background: #0a0a0a; image-rendering: pixelated; }}
  td.thumb {{ width: 160px; }}
  td.id {{ font-family: ui-monospace, "Cascadia Mono", monospace; font-size: 12px;
          width: 200px; word-break: break-all; }}
  td.id .surface {{ color: #888; }}
  td.scores {{ width: 220px; font-family: ui-monospace, monospace; font-size: 12px; }}
  .score-row {{ display: flex; justify-content: space-between; padding: 1px 0; }}
  .tier-keeper   {{ color: #6ee06e; }}
  .tier-ok       {{ color: #b3e06e; }}
  .tier-watch    {{ color: #e0d06e; }}
  .tier-fix      {{ color: #e08a6e; }}
  .tier-critical {{ color: #e06e6e; font-weight: bold; }}
  td.rate select {{ width: 100%; background: #222; color: #e0e0e0;
                   border: 1px solid #444; padding: 6px; border-radius: 3px;
                   font-size: 13px; }}
  td.rate textarea {{ width: 100%; min-height: 70px; background: #222;
                     color: #e0e0e0; border: 1px solid #444; padding: 6px;
                     border-radius: 3px; font-family: inherit; font-size: 12px;
                     box-sizing: border-box; resize: vertical; }}
  td.rate .saved-tag {{ color: #6ab0ff; font-size: 11px; margin-top: 4px;
                      display: block; height: 14px; }}
  td.intent {{ width: 110px; font-size: 11px; color: #aaa; }}
  td.intent.spec_driven {{ color: #b0c8e0; }}
  td.intent.pattern_design {{ color: #c8b0e0; }}
  td.intent.pattern_image {{ color: #e0c8b0; }}
  .nothumb {{ width: 144px; height: 144px; background: #1a0a0a; color: #804040;
              display: flex; align-items: center; justify-content: center;
              font-size: 11px; border: 1px dashed #804040; }}
  .pre-export {{ background: #0a0a0a; color: #b0e0b0; padding: 16px;
                font-family: ui-monospace, monospace; font-size: 11px;
                white-space: pre-wrap; border: 1px solid #2a4a2a; }}
  dialog {{ background: #1a1a1a; color: #e0e0e0; border: 1px solid #444;
           max-width: 80vw; max-height: 80vh; }}
</style>
</head>
<body>
<header>
  <h1>SPB Workbench — {category} <span style="color:#888;font-weight:normal;font-size:14px;">({n_finishes} finishes)</span></h1>
  <div class="meta">
    Category mean composite: <b style="color:#fff;">{cat_mean}</b> &nbsp;|&nbsp;
    Tiers: <span class="tier-keeper">keeper {cat_keeper}</span> /
           <span class="tier-ok">ok {cat_ok}</span> /
           <span class="tier-watch">watch {cat_watch}</span> /
           <span class="tier-fix">fix {cat_fix}</span> /
           <span class="tier-critical">critical {cat_critical}</span>
    &nbsp;|&nbsp;
    <a href="SPB_WORKBENCHES_INDEX.html">← Index</a> &nbsp;
    <a href="SPB_FINISH_QUALITY_WORKBOOK.html">Master workbook</a>
  </div>
  <div class="changes">{changes_html}</div>
  <div class="actions">
    <button onclick="exportRatings()">Export ratings (copy JS block)</button>
    <button class="exp" onclick="postToServer()">POST to local server</button>
    <button onclick="clearLocal()">Clear all local edits</button>
    <span id="status" style="margin-left:12px;color:#6ab0ff;font-size:12px;"></span>
  </div>
</header>
<main>
<table>
  <thead><tr>
    <th>Thumbnail</th>
    <th>Finish</th>
    <th>Intent</th>
    <th>Scores</th>
    <th>Status</th>
    <th>Notes</th>
  </tr></thead>
  <tbody>
{rows}
  </tbody>
</table>
<dialog id="export-dialog">
  <h3>Paste this into <code>paint-booth-0-picker-owner-ratings.js</code></h3>
  <pre class="pre-export" id="export-pre"></pre>
  <button onclick="navigator.clipboard.writeText(document.getElementById('export-pre').textContent);this.textContent='Copied!';">Copy to clipboard</button>
  <button onclick="document.getElementById('export-dialog').close()">Close</button>
</dialog>
</main>
<script>
const CATEGORY = {category_json};
const STORAGE_KEY = "spb_workbench_" + CATEGORY;
const EXISTING = {existing_ratings_json};

function loadDraft() {{
  try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}"); }}
  catch {{ return {{}}; }}
}}

function saveDraft(d) {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(d));
  flashStatus("Saved draft locally");
}}

function flashStatus(msg) {{
  const s = document.getElementById("status");
  s.textContent = msg;
  setTimeout(() => {{ if (s.textContent === msg) s.textContent = ""; }}, 2500);
}}

// Initialize each row from existing + localStorage draft.
function initRows() {{
  const draft = loadDraft();
  document.querySelectorAll("[data-fid]").forEach(row => {{
    const fid = row.dataset.fid;
    const d = draft[fid] || {{}};
    const ex = EXISTING[fid] || {{}};
    const status = d.status ?? ex.status ?? "";
    const notes = d.notes ?? ex.notes ?? "";
    row.querySelector(".status-sel").value = status;
    row.querySelector(".notes-ta").value = notes;
    if (d.status || d.notes) {{
      row.querySelector(".saved-tag").textContent = "(local draft)";
    }} else if (ex.status) {{
      row.querySelector(".saved-tag").textContent = "(from ratings.js)";
    }}
  }});
}}

function persistRow(fid, row) {{
  const draft = loadDraft();
  const status = row.querySelector(".status-sel").value;
  const notes = row.querySelector(".notes-ta").value;
  if (!status && !notes) {{
    delete draft[fid];
  }} else {{
    draft[fid] = {{ status, notes }};
  }}
  saveDraft(draft);
  row.querySelector(".saved-tag").textContent = "(local draft)";
}}

function exportRatings() {{
  const draft = loadDraft();
  const today = new Date().toISOString().slice(0, 10);
  const lines = [];
  for (const fid of Object.keys(draft).sort()) {{
    const r = draft[fid];
    if (!r.status) continue;
    const safe = (r.notes || "").replace(/"/g, '\\"').replace(/\n/g, ' ').slice(0, 280);
    lines.push(`  "${{fid}}": {{`);
    lines.push(`    status: "${{r.status}}",`);
    lines.push(`    source: "owner workbench ${{today}}",`);
    lines.push(`    notes: "${{safe}}",`);
    lines.push(`  }},`);
  }}
  const block = lines.join("\n");
  document.getElementById("export-pre").textContent = block || "(no rated finishes yet)";
  document.getElementById("export-dialog").showModal();
}}

// Tick 89 hotfix: the Electron server listens on 59876 (env SHOKKER_PORT
// overrides). 5000 was a guess; left in as a fallback for non-Electron
// dev setups. We probe each candidate's /api/ping first so failed POSTs
// don't blow through the whole draft.
const SERVER_PORTS = [59876, 5000, 5001, 8080];

async function findServerPort() {{
  for (const p of SERVER_PORTS) {{
    try {{
      const r = await fetch(`http://127.0.0.1:${{p}}/api/ping`, {{ method: "GET", mode: "cors" }});
      if (r.ok) return p;
    }} catch (_) {{ /* try next */ }}
    try {{
      // Some servers don't expose /api/ping; try OPTIONS on the rating endpoint.
      const r = await fetch(`http://127.0.0.1:${{p}}/api/owner-rating`, {{ method: "OPTIONS" }});
      if (r.ok || r.status === 405) return p;
    }} catch (_) {{ /* try next */ }}
  }}
  return null;
}}

async function postToServer() {{
  const draft = loadDraft();
  const entries = Object.entries(draft).filter(([_, r]) => r.status);
  if (!entries.length) {{ flashStatus("No rated finishes to post"); return; }}
  flashStatus("Finding server...");
  const port = await findServerPort();
  if (!port) {{
    flashStatus("ERR: no server reachable on " + SERVER_PORTS.join("/") + ". Use Export instead.");
    return;
  }}
  flashStatus(`Posting to :${{port}}...`);
  let ok = 0, fail = 0, failMsgs = [];
  for (const [fid, r] of entries) {{
    try {{
      const resp = await fetch(`http://127.0.0.1:${{port}}/api/owner-rating`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          // SPB-89 endpoint expects `finish_id`, NOT `fid`. This was the
          // second tick-89 bug — first was wrong port (5000 vs 59876).
          finish_id: fid,
          status: r.status,
          notes: r.notes || "",
          source: "owner workbench " + new Date().toISOString().slice(0, 10),
        }}),
      }});
      if (resp.ok) ok++;
      else {{ fail++; if (failMsgs.length < 3) failMsgs.push(`${{fid}}: HTTP ${{resp.status}}`); }}
    }} catch (e) {{
      fail++; if (failMsgs.length < 3) failMsgs.push(`${{fid}}: ${{e.message}}`);
    }}
  }}
  const msg = `Posted ${{ok}} ok, ${{fail}} failed` + (failMsgs.length ? ` — ${{failMsgs.join("; ")}}` : "");
  document.getElementById("status").textContent = msg;
}}

function clearLocal() {{
  if (!confirm("Clear ALL local edits for " + CATEGORY + "?")) return;
  localStorage.removeItem(STORAGE_KEY);
  location.reload();
}}

document.addEventListener("DOMContentLoaded", () => {{
  initRows();
  document.querySelectorAll("[data-fid]").forEach(row => {{
    const fid = row.dataset.fid;
    row.querySelector(".status-sel").addEventListener("change", () => persistRow(fid, row));
    row.querySelector(".notes-ta").addEventListener("input",
      () => {{ clearTimeout(row._t); row._t = setTimeout(() => persistRow(fid, row), 400); }});
  }});
}});
</script>
</body>
</html>
"""

STATUS_OPTIONS = [
    ("", "— pick —"),
    ("keeper", "keeper"),
    ("watch", "watch"),
    ("rework_paint", "rework_paint"),
    ("rework_spec", "rework_spec"),
    ("reject", "reject"),
]


def build_row(fid: str, sc: dict, m7_byfinish: dict) -> str:
    surface, _, stem = fid.partition(":")
    m7 = m7_byfinish.get(fid, {})
    intent = m7.get("intent", "?")
    tier = m7.get("tier", "unscored")
    composite = m7.get("composite")
    components = m7.get("components", {})

    thumb_rel = find_thumbnail(fid)
    if thumb_rel:
        thumb_html = f'<img src="{escape(thumb_rel)}" alt="{escape(stem)}" loading="lazy">'
    else:
        thumb_html = '<div class="nothumb">(no thumb)</div>'

    comp_html = ""
    if composite is not None:
        comp_html = f'<div class="score-row"><span>composite</span><span class="tier-{tier}">{composite}</span></div>'
        comp_html += f'<div class="score-row" style="color:#888;"><span>tier</span><span>{tier}</span></div>'
        for k in ("m1", "m2", "m5", "m6"):
            v = components.get(k)
            if v is not None:
                comp_html += f'<div class="score-row" style="color:#aaa;"><span>{k.upper()}</span><span>{v}</span></div>'
        clone_size = m7.get("cloneSize", 1)
        if clone_size and clone_size > 1:
            comp_html += f'<div class="score-row" style="color:#e08a6e;"><span>cloneSize</span><span>{clone_size}</span></div>'
    else:
        comp_html = '<span style="color:#888;">(unscored)</span>'

    status_opts = "\n".join(
        f'      <option value="{v}">{escape(t)}</option>'
        for v, t in STATUS_OPTIONS
    )
    return f"""    <tr data-fid="{escape(fid)}">
      <td class="thumb">{thumb_html}</td>
      <td class="id"><span class="surface">{escape(surface)}:</span><br>{escape(stem)}</td>
      <td class="intent {escape(intent)}">{escape(intent)}</td>
      <td class="scores">{comp_html}</td>
      <td class="rate" style="width:140px;"><select class="status-sel">
{status_opts}
    </select>
    <span class="saved-tag"></span></td>
      <td class="rate"><textarea class="notes-ta" placeholder="Verdict notes, what's wrong/right, specific finishes to compare..."></textarea></td>
    </tr>"""


def build_page(category: str, sc: dict, m7: dict, existing: dict) -> str:
    members = [
        fid for fid, entry in sc.items()
        if entry.get("category") == category
    ]
    members.sort()
    m7_byfinish = m7.get("byFinish", {})
    m7_bycat = m7.get("byCategory", {}).get(category, {})
    tiers = m7_bycat.get("tiers", {})

    cat_existing = {fid: existing[fid] for fid in members if fid in existing}

    rows = "\n".join(build_row(fid, sc, m7_byfinish) for fid in members)
    changes = CATEGORY_CHANGE_NOTES.get(
        category,
        "No category-specific engineering notes recorded for this category."
    )

    return HTML_TEMPLATE.format(
        category=escape(category),
        category_json=json.dumps(category),
        n_finishes=len(members),
        cat_mean=m7_bycat.get("meanComposite", "?"),
        cat_keeper=tiers.get("keeper", 0),
        cat_ok=tiers.get("ok", 0),
        cat_watch=tiers.get("watch", 0),
        cat_fix=tiers.get("fix", 0),
        cat_critical=tiers.get("critical", 0),
        changes_html=escape(changes),
        rows=rows,
        existing_ratings_json=json.dumps(cat_existing),
    )


def build_index(generated: list[tuple[str, str, dict]]) -> str:
    """Index page linking every workbench. generated = [(cat, filename, m7_bycat), ...]"""
    rows = []
    for cat, fname, m7_bycat in generated:
        tiers = m7_bycat.get("tiers", {}) if m7_bycat else {}
        rows.append(
            f'<tr><td><a href="{escape(fname)}">{escape(cat)}</a></td>'
            f'<td>{m7_bycat.get("count", "?")}</td>'
            f'<td>{m7_bycat.get("meanComposite", "?")}</td>'
            f'<td class="tier-keeper">{tiers.get("keeper", 0)}</td>'
            f'<td class="tier-ok">{tiers.get("ok", 0)}</td>'
            f'<td class="tier-watch">{tiers.get("watch", 0)}</td>'
            f'<td class="tier-fix">{tiers.get("fix", 0)}</td>'
            f'<td class="tier-critical">{tiers.get("critical", 0)}</td>'
            f'<td style="font-size:12px;color:#aaa;">{escape(CATEGORY_CHANGE_NOTES.get(cat, "")[:120])}</td></tr>'
        )
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>SPB Workbenches — Index</title>
<style>
body {{ font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
        margin:24px;background:#1a1a1a;color:#e0e0e0;}}
h1 {{ margin:0 0 16px;font-size:22px; }}
.intro {{ background:#1f2a1f;border-left:4px solid #4a7c4a;padding:12px 16px;
         margin-bottom:24px;color:#c8e0c8;font-size:13px;line-height:1.4;max-width:1100px;}}
table {{ border-collapse:collapse;width:100%;max-width:1500px;font-size:13px; }}
th,td {{ border:1px solid #2a2a2a;padding:6px 10px;text-align:left; }}
th {{ background:#0f0f0f;color:#aaa; }}
.tier-keeper{{color:#6ee06e;}}.tier-ok{{color:#b3e06e;}}
.tier-watch{{color:#e0d06e;}}.tier-fix{{color:#e08a6e;}}
.tier-critical{{color:#e06e6e;font-weight:bold;}}
a {{color:#6ab0ff;text-decoration:none;}} a:hover {{text-decoration:underline;}}
</style></head><body>
<h1>SPB Category Workbenches</h1>
<div class="intro">
One self-contained editable page per category. Open in any browser — works offline (relative
thumbnail paths). Edit status + notes per finish; auto-saves to localStorage. Use the
"Export ratings" button to copy a paste-ready JS block, or "POST to local server" if the
Electron server is running.
<br><br>
Master workbook: <a href="SPB_FINISH_QUALITY_WORKBOOK.html">SPB_FINISH_QUALITY_WORKBOOK.html</a>
</div>
<table><thead><tr>
<th>Category</th><th>n</th><th>mean composite</th>
<th>keeper</th><th>ok</th><th>watch</th><th>fix</th><th>critical</th>
<th>What changed</th>
</tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table>
</body></html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--category", action="append", default=[],
                    help="Category name (may be repeated). Use exact scorecard name.")
    ap.add_argument("--priority", action="store_true",
                    help="Build the 8 priority categories.")
    ap.add_argument("--fusion-lab", action="store_true",
                    help="Build the 14 fusion-lab categories from owner tick-88 brief "
                         "(~143 finishes).")
    ap.add_argument("--all", action="store_true",
                    help="Build EVERY category present in the scorecard.")
    ap.add_argument("--from-rollup", action="store_true",
                    help="Build categories from m_pattern_weakness_rollup.json priority list.")
    args = ap.parse_args()

    sc = load_scorecard()
    m7 = load_m7()
    existing = load_existing_ratings()
    print(f"[workbench] scorecard={len(sc)}  m7.byFinish={len(m7.get('byFinish',{}))}"
          f"  existing_ratings={len(existing)}")

    # Pick categories.
    all_cats = sorted({entry.get("category") for entry in sc.values() if entry.get("category")})
    if args.all:
        target = all_cats
    elif args.fusion_lab:
        target = [c for c in FUSION_LAB_CATEGORIES if c in all_cats]
    elif args.priority:
        target = [c for c in PRIORITY_CATEGORIES if c in all_cats]
    elif args.from_rollup:
        rollup_path = V5_ROOT / "_workbook_metrics" / "m_pattern_weakness_rollup.json"
        rollup = json.loads(rollup_path.read_text(encoding="utf-8")) if rollup_path.exists() else {}
        target = [c for c in (rollup.get("category_priority") or []) if c in all_cats]
        if not target:
            print(f"[warn] {rollup_path} missing — run scripts/spb_pattern_weakness_rollup.py")
    elif args.category:
        target = []
        for c in args.category:
            if c in all_cats:
                target.append(c)
            else:
                print(f"[warn] category not in scorecard: {c!r}")
    else:
        # Default: priority + fusion-lab union (deduplicated, fusion-lab order
        # preferred so review queue is grouped at the top of the index page).
        seen: set[str] = set()
        target = []
        for c in FUSION_LAB_CATEGORIES + PRIORITY_CATEGORIES:
            if c in all_cats and c not in seen:
                seen.add(c)
                target.append(c)

    if not target:
        print("[workbench] no categories selected")
        return 1

    generated = []
    for cat in target:
        page = build_page(cat, sc, m7, existing)
        slug = slugify(cat)
        fname = f"SPB_WORKBENCH_{slug}.html"
        out = OUT_DIR / fname
        out.write_text(page, encoding="utf-8")
        n_in_cat = sum(1 for e in sc.values() if e.get("category") == cat)
        m7_bycat = m7.get("byCategory", {}).get(cat, {})
        print(f"  wrote {fname:55s}  ({n_in_cat:4d} finishes, mean={m7_bycat.get('meanComposite','?')})")
        generated.append((cat, fname, m7_bycat))

    # Index page.
    index_html = build_index(generated)
    index_path = OUT_DIR / "SPB_WORKBENCHES_INDEX.html"
    index_path.write_text(index_html, encoding="utf-8")
    print(f"  wrote SPB_WORKBENCHES_INDEX.html  ({len(generated)} workbenches indexed)")
    print()
    print(f"Open: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
