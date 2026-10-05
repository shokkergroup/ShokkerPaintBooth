"""Build SPB_AUDIT.html — interactive owner-eye audit workbook.

Per-pattern UI: thumbnail + PASS/FAIL/SKIP toggle + 10 reason checkboxes +
comment + SUBMIT button. Once submitted a card is HIDDEN from view until
the agent marks `agent_addressed_at` (via scripts/mark_audit_addressed.py).
When the agent re-touches a pattern, the card resurfaces at the FRONT of
the queue with a "AGENT UPDATED — RE-REVIEW" badge for owner re-rating.

Auto-saves to SPB_AUDIT.json when served via scripts/audit_server.py.

Run: python scripts/build_audit_workbook.py
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPM8_PATH = ROOT / "_workbook_metrics" / "spm8_spec_pattern.json"
SPM7_PATH = ROOT / "_workbook_metrics" / "spm7_spec_pattern.json"
LOG_PATH = ROOT / "_workbook_metrics" / "spb109_spec_rework_log.json"
AUDIT_JSON_PATH = ROOT / "SPB_AUDIT.json"
THUMBS = ROOT / "thumbnails" / "spec_patterns"
OUT_HTML = ROOT / "SPB_AUDIT.html"

# Canonical failure reasons synthesized from owner verdicts (tick 79 + later).
REASONS = [
    "Looks like generic noise, not the named thing",
    "Too sparse / not enough density",
    "Features too BIG (violates 2048² fineness rule)",
    "Features too SMALL (sub-resolution, can't see)",
    "Wrong/weak color variation (chroma flat)",
    "Empty space FILLED (should stay empty)",
    "Lacks visible structure (just blur/noise)",
    "Same as another pattern (clone)",
    "Generic radial/grid motif (no fingerprint)",
    "Performance too slow",
]


def load_state():
    """Prefer SPM8 scores (the new authoritative metric). Fall back to
    priority_queue last_score if SPM8 JSON is absent."""
    rows = []
    if SPM8_PATH.exists():
        spm8 = json.loads(SPM8_PATH.read_text(encoding="utf-8"))
        for pid, v in spm8.get("by_finish", {}).items():
            if "composite" not in v:
                continue
            rows.append({
                "id": pid,
                "score": float(v.get("composite", 0)),
                "tier": v.get("tier", "?"),
                "attempts": 0,
                "last_tick": None,
                "fsc": v.get("FSC"),
                "mp": v.get("MP"),
                "rt": v.get("RT"),
                "render_ms": v.get("render_ms"),
            })
    else:
        log = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        for e in log.get("priority_queue", []):
            pid = e.get("id")
            if not pid:
                continue
            rows.append({
                "id": pid,
                "score": e.get("last_score", e.get("baseline_score", 0)) or 0,
                "tier": e.get("last_tier", "?"),
                "attempts": e.get("attempts", 0),
                "last_tick": e.get("last_tick"),
            })
    rows.sort(key=lambda r: r["score"])
    return rows


def load_prior_audit() -> dict:
    """Read prior SPB_AUDIT.json (if any) so we can server-side initial-render
    visibility correctly (e.g. for static file:// users)."""
    if not AUDIT_JSON_PATH.exists():
        return {}
    try:
        return json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def thumb_data_uri(pid: str) -> str:
    p = THUMBS / f"{pid}.png"
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def build_html() -> str:
    rows = load_state()
    prior = load_prior_audit().get("entries", {})

    parts = []
    parts.append("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SPB Spec Pattern Audit</title>
<style>
  body { font-family: -apple-system, Segoe UI, sans-serif; margin: 0; padding: 16px; background:#1a1a1a; color:#eee; }
  h1 { margin: 0 0 8px; }
  .toolbar { position: sticky; top: 0; background: #1a1a1a; padding: 8px 0; border-bottom: 1px solid #333; z-index: 10; margin-bottom: 12px; }
  button { background:#2a5; color:#fff; border:0; padding:8px 16px; font-size:14px; cursor:pointer; border-radius:4px; margin-right:8px; }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  button.secondary { background:#444; }
  button.submit { background:#36c; width:100%; margin-top:6px; padding:6px; }
  button.submit.ready { background:#2a5; }
  .filter { background:#222; color:#eee; border:1px solid #444; padding:6px; font-size:14px; }
  .grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(380px,1fr)); gap:12px; }
  .card { background:#222; border:1px solid #333; border-radius:6px; padding:10px; position:relative; }
  .card.PASS { border-color: #2a5; }
  .card.FAIL { border-color: #c34; }
  .card.needs-rereview { border-color: #fc3; box-shadow: 0 0 12px rgba(255,204,51,0.35); }
  .badge { position:absolute; top:-10px; right:8px; background:#fc3; color:#111; padding:3px 8px; border-radius:10px; font-size:11px; font-weight:700; }
  .head { display:flex; gap:10px; align-items:center; margin-bottom:8px; }
  .thumb { width:96px; height:96px; border-radius:4px; background:#000; image-rendering: pixelated; }
  .id { font-weight:700; font-size:14px; word-break:break-all; }
  .score { font-size:12px; color:#aaa; }
  .tier-masterpiece { color:#5ef; font-weight:700 }
  .tier-keeper { color:#4d4 }
  .tier-ok { color:#9c4 }
  .tier-watch { color:#c84 }
  .tier-fix, .tier-critical { color:#c44 }
  .verdict-row { display:flex; gap:6px; margin-bottom:6px; }
  .verdict-row label { padding:4px 10px; background:#333; border-radius:4px; cursor:pointer; font-size:12px; }
  .verdict-row input[type=radio] { display:none }
  .verdict-row input[type=radio]:checked + span { font-weight:700 }
  .verdict-row .v-pass:has(input:checked) { background:#2a5; }
  .verdict-row .v-fail:has(input:checked) { background:#c34; }
  .verdict-row .v-skip:has(input:checked) { background:#666; }
  .reasons { font-size:12px; margin-bottom:6px; }
  .reasons label { display:block; cursor:pointer; padding:1px 0; }
  .comment { width:100%; box-sizing:border-box; background:#1a1a1a; color:#eee; border:1px solid #333; padding:4px; font-family:inherit; font-size:12px; resize:vertical; min-height:34px; }
  .stats { font-size:12px; color:#bbb; margin-left:auto; }
  .last-meta { font-size:11px; color:#888; margin-top:4px; }
  .card.hidden-by-submit { display:none; }
  body.show-submitted .card.hidden-by-submit { display:block; opacity:0.55; }
  body.show-submitted .card.hidden-by-submit::after { content:"submitted — waiting for agent"; position:absolute; top:8px; right:8px; font-size:11px; color:#888; }
</style>
</head>
<body>
<h1>SPB Spec Pattern Audit</h1>
<div class="toolbar">
  <button onclick="downloadJson()">Download Audit JSON</button>
  <button class="secondary" onclick="loadJson()">Load JSON</button>
  <button class="secondary" onclick="clearAll()">Clear all</button>
  <label style="font-size:12px; margin-right:8px;"><input type="checkbox" id="showSubmitted" onchange="toggleShowSubmitted()"> show submitted</label>
  <select id="filter" class="filter" onchange="applyFilter()">
    <option value="all">All patterns</option>
    <option value="fix">Fix/critical only (&lt;55)</option>
    <option value="watch">Watch (55-65)</option>
    <option value="ok">OK (65-80)</option>
    <option value="keeper">Keeper (80+)</option>
    <option value="unaudited">Not yet audited</option>
    <option value="rereview">Needs re-review (agent updated)</option>
    <option value="fail">Marked FAIL (in-progress)</option>
  </select>
  <input type="file" id="jsonFile" accept=".json" style="display:none" onchange="onJsonFile(event)">
  <span id="saveStatus" style="color:#9f6; font-size:12px; margin-left:8px;"></span>
  <span class="stats" id="stats"></span>
</div>
<div class="grid" id="grid">""")

    parts.append('<script id="patterns-data" type="application/json">')
    parts.append(json.dumps(rows))
    parts.append('</script>\n')
    parts.append('<script id="reasons-data" type="application/json">')
    parts.append(json.dumps(REASONS))
    parts.append('</script>\n')
    parts.append('<script id="prior-audit-data" type="application/json">')
    parts.append(json.dumps(prior))
    parts.append('</script>\n')

    for r in rows:
        pid = r["id"]
        score = r["score"]
        tier = r["tier"] or "?"
        attempts = r["attempts"]
        last_tick = r.get("last_tick") or "—"
        thumb = thumb_data_uri(pid)
        tier_class = f"tier-{tier}"
        parts.append(f'<div class="card" data-id="{pid}" data-score="{score}" data-tier="{tier}">')
        parts.append('  <div class="head">')
        if thumb:
            parts.append(f'    <img class="thumb" src="{thumb}" alt="">')
        else:
            parts.append('    <div class="thumb"></div>')
        parts.append('    <div>')
        parts.append(f'      <div class="id">{pid}</div>')
        parts.append(f'      <div class="score"><span class="{tier_class}">{tier}</span> · {score:.1f} · attempts={attempts} · last_tick={last_tick}</div>')
        parts.append(f'      <div class="last-meta" data-meta="{pid}"></div>')
        parts.append('    </div>')
        parts.append('  </div>')
        parts.append('  <div class="verdict-row">')
        parts.append(f'    <label class="v-pass"><input type="radio" name="v_{pid}" value="PASS"><span>PASS</span></label>')
        parts.append(f'    <label class="v-fail"><input type="radio" name="v_{pid}" value="FAIL"><span>FAIL</span></label>')
        parts.append(f'    <label class="v-skip"><input type="radio" name="v_{pid}" value="SKIP"><span>SKIP</span></label>')
        parts.append('  </div>')
        parts.append('  <div class="reasons">')
        for i, reason in enumerate(REASONS):
            parts.append(f'    <label><input type="checkbox" name="r_{pid}" value="{i}"> {reason}</label>')
        parts.append('  </div>')
        parts.append(f'  <textarea class="comment" name="c_{pid}" placeholder="Owner comment (free text)…"></textarea>')
        parts.append(f'  <button class="submit" data-submit="{pid}" disabled onclick="submitCard(\'{pid}\')">Submit (hide until agent updates)</button>')
        parts.append('</div>')

    parts.append('</div>\n')
    parts.append(r"""
<script>
const HAS_SERVER = (location.protocol === 'http:' || location.protocol === 'https:');
let saveTimer = null;
// In-memory live state. Keys = pid. Each entry tracks verdict/reasons/comment
// + submitted_at + agent_addressed_at. agent_addressed_at is set ONLY by the
// agent-side helper (scripts/mark_audit_addressed.py) writing to SPB_AUDIT.json,
// then read back by us via /state.
const liveState = {};

function ensureEntry(pid) {
  if (!liveState[pid]) liveState[pid] = { verdict:null, reasons:[], comment:'', submitted_at:null, agent_addressed_at:null };
  return liveState[pid];
}

function collect() {
  const out = { generated: new Date().toISOString(), entries: {} };
  document.querySelectorAll('.card').forEach(card => {
    const pid = card.dataset.id;
    const verdict = card.querySelector('input[name="v_'+pid+'"]:checked');
    const reasons = Array.from(card.querySelectorAll('input[name="r_'+pid+'"]:checked')).map(i => parseInt(i.value));
    const comment = card.querySelector('textarea[name="c_'+pid+'"]').value.trim();
    const ls = liveState[pid] || {};
    if (verdict || reasons.length || comment || ls.submitted_at || ls.agent_addressed_at) {
      out.entries[pid] = {
        verdict: verdict ? verdict.value : null,
        reasons: reasons,
        comment: comment,
        score: parseFloat(card.dataset.score),
        tier: card.dataset.tier,
        submitted_at: ls.submitted_at || null,
        agent_addressed_at: ls.agent_addressed_at || null,
      };
    }
  });
  return out;
}

function downloadJson() {
  const data = collect();
  const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'SPB_AUDIT.json';
  document.body.appendChild(a); a.click(); a.remove();
}

function loadJson() {
  document.getElementById('jsonFile').click();
}

function onJsonFile(e) {
  const f = e.target.files[0]; if (!f) return;
  const r = new FileReader();
  r.onload = () => {
    try { applyData(JSON.parse(r.result)); }
    catch(err) { alert('Bad JSON: '+err); }
  };
  r.readAsText(f);
}

function applyData(data) {
  const entries = (data && data.entries) || {};
  Object.entries(entries).forEach(([pid, e]) => {
    const ls = ensureEntry(pid);
    ls.submitted_at = e.submitted_at || null;
    ls.agent_addressed_at = e.agent_addressed_at || null;
    if (e.verdict) {
      const v = document.querySelector('input[name="v_'+pid+'"][value="'+e.verdict+'"]');
      if (v) v.checked = true;
      ls.verdict = e.verdict;
    }
    (e.reasons||[]).forEach(idx => {
      const r = document.querySelector('input[name="r_'+pid+'"][value="'+idx+'"]');
      if (r) r.checked = true;
    });
    ls.reasons = e.reasons || [];
    if (e.comment) {
      const c = document.querySelector('textarea[name="c_'+pid+'"]');
      if (c) c.value = e.comment;
      ls.comment = e.comment;
    }
    refreshCard(pid);
  });
  sortGrid();
  applyVisibility();
  updateStats();
}

function clearAll() {
  if (!confirm('Clear all audit entries (verdicts, reasons, comments, submitted state)?')) return;
  document.querySelectorAll('input[type=radio],input[type=checkbox]').forEach(i => i.checked = false);
  document.querySelectorAll('textarea').forEach(t => t.value = '');
  document.querySelectorAll('.card').forEach(c => {
    c.classList.remove('PASS','FAIL','needs-rereview','hidden-by-submit');
    const badge = c.querySelector('.badge'); if (badge) badge.remove();
  });
  Object.keys(liveState).forEach(k => delete liveState[k]);
  updateStats();
  autoSave(true);
}

function refreshCard(pid) {
  const card = document.querySelector('.card[data-id="'+pid+'"]');
  if (!card) return;
  card.classList.remove('PASS','FAIL');
  const v = card.querySelector('input[name="v_'+pid+'"]:checked');
  if (v) card.classList.add(v.value);
  // Enable submit button only when verdict picked
  const sub = card.querySelector('button.submit');
  if (sub) {
    sub.disabled = !v;
    sub.classList.toggle('ready', !!v);
  }
}

function needsReReview(pid) {
  const ls = liveState[pid];
  if (!ls || !ls.submitted_at) return false;
  if (!ls.agent_addressed_at) return false;
  return new Date(ls.agent_addressed_at).getTime() > new Date(ls.submitted_at).getTime();
}

function isHiddenBySubmit(pid) {
  const ls = liveState[pid];
  if (!ls || !ls.submitted_at) return false;
  // Hidden only if no agent activity since the submit
  if (!ls.agent_addressed_at) return true;
  return new Date(ls.agent_addressed_at).getTime() <= new Date(ls.submitted_at).getTime();
}

function applyVisibility() {
  document.querySelectorAll('.card').forEach(c => {
    const pid = c.dataset.id;
    const hide = isHiddenBySubmit(pid);
    c.classList.toggle('hidden-by-submit', hide);
    const rr = needsReReview(pid);
    c.classList.toggle('needs-rereview', rr);
    // Badge
    let badge = c.querySelector('.badge');
    if (rr) {
      if (!badge) {
        badge = document.createElement('div');
        badge.className = 'badge';
        c.appendChild(badge);
      }
      badge.textContent = '🔁 AGENT UPDATED — RE-REVIEW';
    } else if (badge) {
      badge.remove();
    }
    // Last-meta line
    const meta = c.querySelector('.last-meta');
    if (meta) {
      const ls = liveState[pid] || {};
      const bits = [];
      if (ls.submitted_at) bits.push('submitted ' + ls.submitted_at.replace('T',' ').slice(0,19));
      if (ls.agent_addressed_at) bits.push('agent ' + ls.agent_addressed_at.replace('T',' ').slice(0,19));
      meta.textContent = bits.join(' · ');
    }
  });
  applyFilter();
}

function sortGrid() {
  // Order: needs-rereview first (newest agent_addressed_at first), then
  // unsubmitted (worst score first), then submitted-and-waiting last.
  const grid = document.getElementById('grid');
  const cards = Array.from(grid.querySelectorAll('.card'));
  cards.sort((a, b) => {
    const pa = a.dataset.id, pb = b.dataset.id;
    const rrA = needsReReview(pa), rrB = needsReReview(pb);
    if (rrA !== rrB) return rrA ? -1 : 1;
    if (rrA && rrB) {
      // Newest agent activity first
      return new Date(liveState[pb].agent_addressed_at) - new Date(liveState[pa].agent_addressed_at);
    }
    const subA = isHiddenBySubmit(pa), subB = isHiddenBySubmit(pb);
    if (subA !== subB) return subA ? 1 : -1;
    return parseFloat(a.dataset.score) - parseFloat(b.dataset.score);
  });
  cards.forEach(c => grid.appendChild(c));
}

function updateStats() {
  let pass=0, fail=0, skip=0, none=0, submitted=0, rereview=0;
  document.querySelectorAll('.card').forEach(c => {
    const pid = c.dataset.id;
    const v = c.querySelector('input[name="v_'+pid+'"]:checked');
    if (!v) none++;
    else if (v.value==='PASS') pass++;
    else if (v.value==='FAIL') fail++;
    else if (v.value==='SKIP') skip++;
    if (isHiddenBySubmit(pid)) submitted++;
    if (needsReReview(pid)) rereview++;
  });
  document.getElementById('stats').textContent =
    `PASS ${pass} · FAIL ${fail} · SKIP ${skip} · unaudited ${none} · submitted(hidden) ${submitted} · re-review ${rereview}`;
}

function applyFilter() {
  const f = document.getElementById('filter').value;
  document.querySelectorAll('.card').forEach(c => {
    const score = parseFloat(c.dataset.score);
    const pid = c.dataset.id;
    const v = c.querySelector('input[name="v_'+pid+'"]:checked');
    let show = true;
    if (f==='fix') show = score<55;
    else if (f==='watch') show = score>=55 && score<65;
    else if (f==='ok') show = score>=65 && score<80;
    else if (f==='keeper') show = score>=80;
    else if (f==='unaudited') show = !v;
    else if (f==='fail') show = v && v.value==='FAIL';
    else if (f==='rereview') show = needsReReview(pid);
    // We don't toggle display here for submitted-hidden — that's handled by CSS
    // class .hidden-by-submit + body.show-submitted. We just respect filter on
    // visible cards.
    c.style.display = show ? '' : 'none';
  });
}

function toggleShowSubmitted() {
  const on = document.getElementById('showSubmitted').checked;
  document.body.classList.toggle('show-submitted', on);
}

function submitCard(pid) {
  const card = document.querySelector('.card[data-id="'+pid+'"]');
  if (!card) return;
  const v = card.querySelector('input[name="v_'+pid+'"]:checked');
  if (!v) { alert('Pick PASS / FAIL / SKIP first.'); return; }
  const ls = ensureEntry(pid);
  ls.submitted_at = new Date().toISOString();
  // Clear any stale agent_addressed_at older than now (it will be set by agent later)
  if (ls.agent_addressed_at && new Date(ls.agent_addressed_at) <= new Date(ls.submitted_at)) {
    // leave stale value — visibility logic ignores when <= submitted_at
  }
  applyVisibility();
  sortGrid();
  updateStats();
  autoSave(true);
}

function autoSave(force) {
  if (!HAS_SERVER) return;
  if (saveTimer) clearTimeout(saveTimer);
  const delay = force ? 0 : 250;
  saveTimer = setTimeout(async () => {
    try {
      const data = collect();
      const r = await fetch('/save', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
      const txt = await r.text();
      const s = document.getElementById('saveStatus');
      if (s) { s.textContent = '✓ ' + txt; setTimeout(()=>{ if(s.textContent.startsWith('✓ ')) s.textContent=''; }, 2000); }
    } catch(e) {
      const s = document.getElementById('saveStatus');
      if (s) s.textContent = '✗ save failed: ' + e;
    }
  }, delay);
}

// auto-refresh card colour, stats, and auto-save on any change
document.addEventListener('change', e => {
  if (e.target.matches('input[name^="v_"]')) {
    const pid = e.target.name.slice(2);
    ensureEntry(pid).verdict = e.target.value;
    refreshCard(pid);
  }
  if (e.target.matches('input[name^="r_"]')) {
    const pid = e.target.name.slice(2);
    const reasons = Array.from(document.querySelectorAll('input[name="r_'+pid+'"]:checked')).map(i => parseInt(i.value));
    ensureEntry(pid).reasons = reasons;
  }
  updateStats();
  autoSave();
});
document.addEventListener('input', e => {
  if (e.target.matches('textarea.comment')) {
    const pid = e.target.name.slice(2);
    ensureEntry(pid).comment = e.target.value.trim();
    autoSave();
  }
});

// Restore state. Priority: live server /state. Fallback: inline prior-audit-data
// (so file:// works after server has been run at least once and saved JSON).
async function restoreState() {
  let restored = false;
  if (HAS_SERVER) {
    try {
      const r = await fetch('/state', {cache:'no-store'});
      const data = await r.json();
      if (data && data.entries) { applyData(data); restored = true; }
    } catch(e) { /* fall through */ }
  }
  if (!restored) {
    try {
      const inline = JSON.parse(document.getElementById('prior-audit-data').textContent || '{}');
      if (inline && Object.keys(inline).length) applyData({entries: inline});
    } catch(e) {}
  }
  // even without restore, sort + visibility
  sortGrid();
  applyVisibility();
  updateStats();
}

// Periodically poll /state for agent updates so re-review cards surface
// without manual refresh.
async function pollAgentUpdates() {
  if (!HAS_SERVER) return;
  try {
    const r = await fetch('/state', {cache:'no-store'});
    const data = await r.json();
    if (data && data.entries) {
      let changed = false;
      Object.entries(data.entries).forEach(([pid, e]) => {
        const ls = ensureEntry(pid);
        const newAgent = e.agent_addressed_at || null;
        if (newAgent && newAgent !== ls.agent_addressed_at) {
          ls.agent_addressed_at = newAgent;
          changed = true;
        }
      });
      if (changed) { applyVisibility(); sortGrid(); updateStats(); }
    }
  } catch(e) {}
}
setInterval(pollAgentUpdates, 8000);

restoreState();
</script>
</body>
</html>
""")
    return "".join(parts)


def main():
    html = build_html()
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_HTML} ({OUT_HTML.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
