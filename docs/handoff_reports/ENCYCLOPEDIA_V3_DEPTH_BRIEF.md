# Encyclopedia v3 — DEPTH + REAL PICTURES brief (orchestrator, 2026-10-04 evening)

Owner: "Not a BAD start ... the picture examples would be better with ACTUAL pictures from the app ... ACTUAL images that make it look like what people are seeing ... the Encyclopedia itself can use even MORE detail, knowledge. We can't have too much knowledge built in. It needs to be smarter than all hell and actually impress people with everything they can learn."
Standing rules still apply: `ENCYCLOPEDIA_V2_WRITER_BRIEF.md` (facts from code/data/wiki with sources, plain buyer words, incremental atomic writes, generators for per-item pages, your files only). **Easy mode is HIDDEN — never mention it** (`scripts/ai_atlas/enc_hidden_features.json`).

**NO SUB-AGENTS (owner cap: 5–6 agents TOTAL, orchestrator owns the fleet).** Do all work yourself; never call the Agent/Task tool. Lanes A and B each spawned helpers on 2026-10-04 and pushed the fleet to ~10 — never again.

## Schema v3 (additive — lane A updates `data/encyclopedia/_schema.md` + `enc_v2_test.js` FIRST)
New optional article fields:
- `deep[]` {heading, body} — "How it really works": the engine-level truth in buyer words, with real numbers (ranges, defaults, channel values, order of operations, what overrides what).
- `examples[]` {title, goal, settings{label:value}, result, screen?} — 2–4 worked examples with EXACT settings a buyer can copy.
- `combos[]` {with (id), why} — what pairs well / clashes, and why.
- `faq[]` {q, a} — 3–8 real questions a buyer would ask (mine js/spb-support-answers.js, the copilot test corpora in `_easy_claude_work/*corpus*`, the owner's own asks in docs/handoff_reports/*).
- `mistakes[]` {symptom, cause, fix}.
- `protips[]` — non-obvious knowledge (from wiki Hard-Won Lessons, feedback memories surfaced in docs, Viva Mexico masterclass) — the "I didn't know it could do that" layer.
- `screens[]` — ids of REAL app screenshots (lane S manifest `data/encyclopedia/screens.json`).
- `level` — beginner | intermediate | pro.

## Depth bar (gate-enforced per hand-written article)
Core article: summary + what + ≥3 how steps + ≥2 `deep` sections + ≥2 `examples` + ≥3 `faq` + ≥2 `mistakes` + ≥1 `protips` + ≥1 `screens` (once lane S has ids) — and every number sourced. Short Q&A help pages (the 224 `help_*` pages) are upgraded to real articles: steps + why + mistakes + related. Finish/pattern pages gain generated depth: exact spec character (M/R/CC from the registry), category intent, best paint colours/contrast, combos, a REAL render tile (lane S).

## Lane S — REAL APP PICTURES
Playwright on test server 127.0.0.1:59879 ONLY (own Chrome profile/port; never 59876), harness pattern `_easy_claude_work/pw/ft_inapp.py`. Load REAL cars (owner examples `C:/1Shokker Paint Car Examples`, the owner PSD the harness uses). Produce what buyers SEE: every panel/tool/dialog as a cropped screenshot with numbered callouts (drawn on top by a script, matching the app style); before/after pairs (zone added, finish applied, spec slider moved, pattern scaled, layer hidden, render preview vs export); finish tiles rendered ON A CAR (not balls) for every finish category + the top finishes per category; spec map channel views from the app's own R METAL / G ROUGH / B COAT panes. Hide Wire/Mask/Car Mandatory + call `_finishLayerVisibilityChange()` before car shots. WebP ≤ 250 KB each; manifest `data/encyclopedia/screens.json` {id, title, caption, file, alt, article_ids[], kind: ui|before_after|car_render|spec_view}. LOOK at every image before it counts. Replace redrawn charts in articles where a real picture is clearer (keep SVGs that explain a concept no screenshot can).
