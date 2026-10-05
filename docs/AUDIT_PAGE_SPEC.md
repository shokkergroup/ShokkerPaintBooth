# SPB Audit Page — Build Spec (the "refer to it EVERY TIME" doc)

**Owner mandate (2026-06-09):** When Ricky says *"create an audit HTML page for &lt;bases / patterns / spec overlays / finishes / a combo&gt;,"* follow THIS document. He should never have to re-explain the audit process. Build it, render the swatches, wire it to the server, hand him the URL. When he says *"look through the audit,"* read the verdicts back and act on them (below).

---

## 1. The loop (what the whole thing is for)

```
BUILD items  ->  AUDIT page (he rates)  ->  verdicts persist server-side  ->
"look through the audit"  ->  I read verdicts  ->  act (keep/remove/rebuild/replace/rename)  ->
regenerate the audit page with ONLY the items needing another round  ->  repeat until all clean
```

Rated items **disappear from the page** once decided (he only ever sees what still needs a verdict). The cycle ends when every item is `keep` (or removed).

---

## 2. Backend — ALREADY BUILT, do not reinvent (`server_routes/june_audit_routes.py`)

- **Submit:** `POST /api/june-audit/<category>` — body `{"entries": {item_id: {verdict, rating, ai_rating, reasons:[...], notes, ts}}}`. Merges by newest `ts` per id; appends to history.
- **Recall (preload + hide-rated):** `GET /api/june-audit/<category>` — returns `{entries, total, counts}`. The page calls this on load and **hides any item that already has a verdict**.
- **Verdict vocabulary:** `keep | rebuild | replace | rename | remove`. (Map Ricky's words: **Keep**=keep, **Replace**=replace, **Rebuild**=rebuild, **Rename**=rename. `remove` = cut entirely.)
- **`rating`** = owner 1–100 slider (optional). **`ai_rating`** = the engine's current score baked into the page so we see how far off we are (optional).
- **`reasons`** = array of short "why it failed" chips (≤60 chars each, ≤20). **`notes`** = free text (≤4000 chars).
- **Category** = any `^[a-z0-9_]{1,40}$` key (e.g. `finish`, `pattern`, `spec_overlay`, `lfr_finish`). No backend edit needed for a new category.
- **Storage I can read back:**
  - `electron-app/server/_audit/june_<category>_audit.json` — current verdict per id (`{"entries": {id: {...}}}`).
  - `electron-app/server/_audit/june_<category>_audit_history.jsonl` — append-only submit log.
  - (In dev, same paths under the running server's dir. When Ricky says "look through the audit," READ this json.)
- **Page serving (generic, zero backend change):** name the file `SPB_AUDIT_<name>.html`, put it at repo root (it syncs to the mirror), and it's served at `/SPB_AUDIT_<name>.html` automatically. (The three legacy `SPB_JUNE_AUDIT_{SPEC_OVERLAYS,BASES,PATTERNS}.html` still serve too.)

---

## 3. Frontend — the audit page template (self-contained HTML)

One file, no build step, served by the route above. Structure:

1. **Self-contained:** inline `<style>` + `<script>`; no external deps. Match the SPB dark aesthetic (see existing `SPB_JUNE_AUDIT_*.html` for the look).
2. **Swatch per item:** render each item to a PNG **before** building the page (see §4) and reference it (served path `thumbnails/audit/<category>/<id>.png`, or a data-URI for full portability). Show a big, honest swatch — the thing being judged.
3. **Card per item** containing: the swatch, the item **name** + **id**, a one-line description, the **`ai_rating`** badge, then the verdict controls:
   - **Verdict buttons:** `Keep` · `Replace` · `Rebuild` · `Rename` (and a quieter `Remove`). One active at a time.
   - **Owner rating slider** 1–100 (optional, step 1).
   - **"Why it failed" chips** (multi-select) — category-specific (see §5). These populate `reasons[]`.
   - **Notes** textarea.
4. **PER-CARD SUBMIT (owner mandate 2026-06-09):** every card has its own **SUBMIT THIS ONE** button that POSTs that single entry immediately and fades the card — Ricky can submit a few, tell Claude to act on what's submitted, and keep rating the rest. The sticky bar keeps live counts + a secondary **Submit ALL decided** bulk button, and auto-save to `localStorage` so a refresh never loses work.
5. **Hide-on-decide:** on load, `GET` the verdicts and **remove already-rated cards** from the DOM; after a successful submit, fade out the just-decided cards. He only sees undecided items. **Loop rule:** when Claude REBUILDS or REPLACES an item, clear that id from `_audit/june_<category>_audit.json` so the redone item REAPPEARS for re-review; keep/remove/rename verdicts stay hidden forever.
6. **`ts`:** stamp each entry with `Date.now()` so the newest decision wins across tabs.
7. **Badges:** `ai_rating` (structure meter), `MIP` (detail retention at 1/4 view), and **⏱ render time** measured at REAL size (owner doctrine: ~1s optimal, >3s unacceptable — red badge). Use `scripts/spb_audit_page_builder.py` — it implements all of this; per-category pages are thin wrappers (see `scripts/lfr_build_audit_page.py` / `scripts/fable_build_audit_page.py`).

> The page is THROWAWAY per round — regenerate it each cycle from the current item set minus anything already `keep`/`remove`.

---

## 4. Rendering the swatches (before building the page)

- Render each new item through the **booth's own render path** (the same engine the app uses) so the swatch is truthful — never a fake gradient.
- Save to `thumbnails/audit/<category>/<id>.png` (a small batch script, mirrors `rebuild_picker_swatches.py`). The page `<img src>` points there (served statically) OR embeds as a data-URI for a fully portable single file.
- **Spec overlays:** show the COMBINED M/R/Cc composite **and** (ideally) the overlay applied on a neutral base, so the angle/spec behavior reads. **Finishes/patterns:** show on a representative car zone or a flat tile at a sane scale.

---

## 5. "Why it failed" chip taxonomies (per category) — EXPANDED 2026-06-09

Multi-select, checkbox-style ("WHAT'S WRONG — check any"). The canonical lists live in
`scripts/spb_audit_page_builder.py` (`COMMON_CHIPS` + `KIND_EXTRA`):

- **Common (every kind):** `Too similar to another` · `Too blobby / macro` · `Too noisy / busy` · `Too flat / boring` · `Not enough fine detail` · `Broken / artifacts` · `Wrong vibe for name` · `Low effort / lazy` · `Colors muddy` · `Clips / blown out` · `Too dark on car` · `Too bright / washed out` · **`Render time too long`** (standing chip — render doctrine: ~1s, >3s unacceptable) · `Other (see notes)`.
- **Finishes extra:** `Weak spec colors` · `Spec wrong for paint` · `No depth`.
- **Patterns extra:** `Doesn't tile / seams` · `Wrong scale` · `Too sparse`.
- **Spec overlays extra:** `Weak spec colors` · `Channels correlated / single-hue` · `No angle reveal` · `Too subtle on car` · `Too harsh` · `Dead/flat zone`.

---

## 6. When Ricky says "look through the audit"

1. Read `_audit/june_<category>_audit.json` (and the history jsonl for context).
2. Bucket by verdict: **keep** → finalize/ship; **remove** → delete the item cleanly (catalog + engine, both copies); **rebuild** → re-author the item's algorithm (read the `reasons`/`notes`); **replace** → design a brand-new item for that slot (NOT a tweak — fresh identity); **rename** → keep the build, change name/id (update all references).
3. Apply the diversity doctrine (see [[spb-spec-diversity-doctrine]]): rebuilds/replacements get a NEW identity — **never** recycle. Use the notes to understand the miss.
4. Re-render swatches for changed items, regenerate `SPB_AUDIT_<name>.html` with ONLY the items still needing a verdict, and tell Ricky it's ready for round N+1.
5. The `_audit` json is the source of truth across sessions — it survives restarts, so the loop resumes cleanly.

---

## 7. Build checklist (every new audit page)

- [ ] Items built + rendered to `thumbnails/audit/<category>/`.
- [ ] `SPB_AUDIT_<name>.html` at repo root, self-contained, matches SPB dark style.
- [ ] Verdict buttons = Keep/Replace/Rebuild/Rename (+ Remove); fail-chips per §5; notes; optional rating + ai_rating.
- [ ] `GET /api/june-audit/<category>` on load → hide decided. `POST` on submit. localStorage autosave. `ts` stamped.
- [ ] `node scripts/sync-runtime-copies.js --write` (the page is a 2-copy file) + restart server (new route/page needs a fresh server).
- [ ] Hand Ricky the URL: `http://127.0.0.1:<port>/SPB_AUDIT_<name>.html`.
