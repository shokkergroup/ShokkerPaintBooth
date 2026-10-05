# ChatGPT / Codex parallel lanes for FINISH INTELLIGENCE (2026-10-02)

Written by Claude for the owner. Claude is working all night on the offline finish advisor (`js/spb-pro-advisor.js`, `js/spb-pro-rank.js`, `js/spb-ai-cards.js`, the card data, `js/spb-pro-ai.js`, `mcp/server/**`, `scripts/ai_atlas/**`). Everything below is **data, tests, audits and reports in a separate folder**, so it never edits a file Claude is editing. Claude merges the results with scripts.

## Paste-ready start prompt

> You are the Codex/ChatGPT agent for Shokker Paint Booth. First open `SPB_WIKI.html` (Start Here, The Laws, Agent Coordination Board) and `AGENTS.md`. Then read `docs/CODEX_FINISH_INTEL_PARALLEL_2026-10-02.md` and pick lanes in the order L1 → L7 (work as many as you have capacity for; one lane at a time, finish and hand off each before starting the next). Claim ONE board row ("Codex — finish-intel parallel lanes", files: `_codex_work/finish_intel/**` only). Write every output ONLY under `_codex_work/finish_intel/`, append JSONL after every completed unit (never write-at-end-only), and leave a `HANDOFF.md` in that folder listing what is ready to merge. Do not edit any file outside that folder except your one board row and ONE daily-log entry. Do not restart any server, do not touch the live app (port 59876), do not author or change any finish, engine file or catalogue entry.

## Hard rules (every lane)
1. **Own folder only:** `_codex_work/finish_intel/` (subfolder per lane: `l1_card_audit/`, `l2_truth_asks/` ...). Read anything; write only there.
2. **Never edit:** `js/**`, `engine/**`, `mcp/**`, `scripts/**`, `_atlas_cards/**`, `_easy_claude_work/**`, `paint-booth-v2.html`, `SPB_WIKI.html` (except your one board row + one log entry), `electron-app/**`. If you find a bug, put it in a report with a repro; Claude fixes it.
3. **Servers:** if a lane needs a server, use your own: `SHOKKER_PORT=59881 python server_v5.py` (Claude's test server is 59879, the owner's live app is 59876). Chrome debugging port 9556 (Claude uses 9555). Stop your server when done.
4. **Judge by eye:** the project law is "never report a gate green without looking" — for anything visual, open the contact sheet / thumbnail yourself.
5. **Token efficiency (owner mandate):** incremental output, filtered command output, no echo-backs of big files, no fan-out of sub-agents.
6. **Read the owner doctrine before judging looks:** `docs/FINISH_LAW.md`, memory-style rules in `CLAUDE.md` (fine 8–32 px micro-texture fields, not posters; "no laziness, no repeats").

## The data you will work with
- `_atlas_cards/items.json` — 4,799 catalogue items: `k` key (`base::…`, `monolithic::…`, `pattern::…`, `spec::…`), `n` name, `d` description, `o` (1 = brings its own colours, 0 = takes the colour you give it), measured `L` lightness, `S` saturation, `V` contrast, `shine`, `metal`, `sp` sparkle, `fb` texture, `M/R/C` spec means, `t` tags, `shelves`.
- `_atlas_cards/cards.jsonl` — one LLM-written card per item (`look`, `analog`, `syn` search words, `mood`, `era`, `use`, `pair`, `avoid`, `loud` 1–5, `busy` 1–5, `scale`) and `_atlas_cards/ratings.jsonl` (`appeal body accent hero risk`).
- Pictures: `thumbnails/` (baked swatches), `_atlas_cards/thumbs/`, contact sheets `_atlas_cards/sheets/` (6 siblings per sheet, numbered tiles).
- Gold asks (356, 10 categories): `_easy_claude_work/gold/asks.json` (`{ask, cat}`) — read-only, copy it if you need to extend.
- Headless harness (read-only use, run from the repo root): `node _easy_claude_work/adv_fp.js <prompts.txt>` (which prompts the advisor claims, one per line), `node _easy_claude_work/more_test.js "ask 1" "ask 2" …` (multi-turn conversation with the real advisor), `node _easy_claude_work/cards_test.js`.
- Physics facts you may rely on: iRacing multiplies paint by the metal level (a coloured full-metal finish goes dark); spec R = metal, G = roughness, B = clearcoat (16 = max gloss). Foundation `f_*` bases are pure solid spec (keep the paint colours); 3,839 of 4,179 finishes bring their own colours and REPLACE a livery colour.

---

## L1 — Second-opinion audit of the finish cards  (biggest accuracy win)
**Why:** the cards are what every AI tier (offline, Claude/OpenAI via MCP, DeepSeek) reads. One annotator (DeepSeek flash) wrote all 4,799; a second, independent reader will catch the errors a single pass misses.
**Do:** for each card, compare `look/syn/analog/mood/loud/busy/pair/avoid` with the item's picture and measured numbers (open the sheet for the item). Flag: look contradicts the picture or numbers (matte vs shine, metallic vs `metal`), colour words on a takes-colour item (`o = 0` must not say "red"/"grey" unless the material itself is that colour), `loud`/`busy` off by 2 or more, search words that are false or too generic ("pattern", "design"), sibling cards that are not distinguishable. Start with a stratified 600-card sample (all shelves, all types), then continue in shelf order.
**Output:** `l1_card_audit/audit.jsonl`, one line per card: `{"k":"base::…","verdict":"ok|fix|bad","issues":[{"field":"look|syn|loud|busy|mood|pair|avoid|analog","problem":"…","suggest":"…"}],"confidence":0.0-1.0}`. Plus `l1_card_audit/summary.md` (counts per shelf and per issue type, the 30 worst examples with item keys).
**Done when:** ≥600 sampled, summary written, `HANDOFF.md` says which shelves are fully covered. Claude re-annotates the `fix`/`bad` cards and re-measures with the picture judge.

## L2 — Ground-truth ask set (a yardstick that does not depend on an AI judge)
**Why:** today quality is measured by a vision model; a hand-labelled truth set is stricter and catches judge blind spots.
**Do:** write **400 new painter-voice asks** in the owner's real voice (casual, typos allowed, some long with a scheme, car class, sponsors, sim constraints). Categories: the 10 gold categories plus real iRacing contexts (series conventions, night races, wet track, TV readability, sponsor-heavy cars, team heritage tributes, famous liveries "Gulf-style", "Martini stripes", multi-constraint asks, "like X but …"). For every ask label 3–8 catalogue finishes that genuinely fit (browse the atlas/cards/thumbnails; use real keys) and 0–5 finishes that would be a WRONG answer.
**Output:** `l2_truth_asks/truth_asks.json` = `[{"ask":"…","cat":"…","part":"stripes|hood|body|…|null","scheme":["navy","orange"]|null,"good":["base::…"],"bad":["monolithic::…"],"notes":"why these"}]`, appended in batches of 25 to `truth_asks.partial.jsonl` first. Keys must exist in `_atlas_cards/items.json`.
**Done when:** 400 asks, every key validated by a script you also leave in the folder (`validate_truth.py`).

## L3 — Messy-prompt corpus for the intent classifier
**Why:** the advisor decides "is this a finish question or something else" with rules; real buyers type messy things.
**Do:** write **1,500 realistic chat messages** with an expected intent label: `recommend | find | compare | about | kit | review | taste | judge | inspect | catalogue | design (build/change a livery) | support (render/export/iRacing/app problems) | none`. Include typos, slang, voice-to-text run-ons, multi-sentence messages, emoji, ALL CAPS, non-native phrasing, and **at least 400 hard negatives** that contain finish words but are about something else ("my chrome stripes won't export", "why is the matte layer black in iRacing").
**Output:** `l3_intent_corpus/intent_corpus.jsonl`: `{"text":"…","intent":"…","note":"optional"}` plus `l3_intent_corpus/prompts_finish.txt` and `prompts_other.txt` (one text per line, for `adv_fp.js`).
**Done when:** 1,500 lines, ≥400 negatives, label distribution table in `summary.md`.

## L4 — Painter vocabulary + colour dictionary
**Why:** the offline search expands words through a hand-written lexicon (~200 entries) and the colour parser knows ~100 colours.
**Do:** propose **600 terms** painters/racers/car-culture people actually type (rattle-can, murdered-out, cerakote, matte wrap, candy apple, gulf, martini, dazzle, patina, "Hot Wheels", team-colour nicknames, slang, common misspellings) with the plain catalogue words they should expand to, and **300 named colours with hex** (e.g. "papaya", "british racing green", "gulf blue", "sunset orange"). Verify each proposed expansion by running a search in the harness and looking at the top results (use `node _easy_claude_work/cards_test.js` as the template; write your own copy under your folder).
**Output:** `l4_vocab/lexicon_proposals.json` = `[{"term":"murdered out","expands_to":["black","matte","stealth","dark"],"example_ask":"…","top_hits_checked":["base::flat_black"],"false_match_risk":"low|medium|high"}]` and `l4_vocab/colour_proposals.json` = `[{"name":"papaya","hex":"#ff7f00","aliases":[…]}]`.
**Done when:** both files complete, each item either verified or marked unverified.

## L5 — Catalogue gap report (what painters ask for that we cannot give)
**Why:** the clearest signal for where new finishes would help (without anyone authoring finishes yet).
**Do:** run the 356 gold asks + your L2 asks through a **copy** of the harness (copy `scripts/ai_atlas/gold_run.js` into your folder and change its output path; do NOT run it in place, it writes into Claude's results folder). Look at the top-6 for every ask on a contact sheet; list the asks where nothing fits. Cluster them into **40–100 gaps** ("white flake over ice blue", "fade from matte to gloss along the car", "worn/chipped race-car look").
**Output:** `l5_gaps/gaps.json` = `[{"gap":"…","example_asks":["…"],"closest_existing":["base::…"],"why_not_enough":"…","priority":"high|medium|low","brief":"one paragraph describing the look at car scale, 8–32 px fields, per docs/FINISH_LAW.md"}]` and `l5_gaps/gap_report.md`. **Briefs only — do not author finishes.**

## L6 — Independent adversarial code review + new node tests
**Why:** Claude just fixed 15 findings from one independent review; a second reviewer with different habits finds different bugs.
**Do:** review `js/spb-pro-advisor.js`, `js/spb-pro-rank.js`, `js/spb-ai-cards.js` and the finish-advisor parts of `js/spb-pro-ai.js` (search for `advisorIntent`, `advisorSearch`, `useKit`, `useFinishCard`). Look for wrong answers, crashes, state bugs across turns, apply-plan mistakes (wrong zone, wrong priority, colours changed when they must not be), regex false positives/negatives, performance traps. For every finding give a **node repro** using the harness (exact asks + zone state).
**Output:** `l6_review/findings.md` (ranked, each with repro command and expected vs actual) and new test files under `l6_review/tests/` in the style of `_easy_claude_work/adv_test.js` / `more_test.js` (they must run with plain `node` from the repo root and print PASS/FAIL).

## L7 — The OpenAI tier for real: drive the SPB MCP tools as a buyer would
**Why:** the owner expects many buyers to connect their ChatGPT/Codex account through MCP. You ARE that tier, so your experience is the best test of the tool descriptions and results.
**Do:** read `docs/CODEX_MCP_SUPPORT_2026-10-01.md` and `mcp/server/tools.json`. Start your own test server on **59881** (Rule 3) with a car loaded and open the app page for that server in a browser tab (the MCP server long-polls the open page) and run the MCP server from source with `SPB_PORT=59881` and its own `SPB_MCP_TOKEN_FILE` (see the header of `mcp/server/index.js` and `docs/CODEX_MCP_SUPPORT_2026-10-01.md`; the packaged `.mcpb` is not rebuilt yet, so `spb_suggest_finishes` exists only in source). Never point it at port 59876: that is the owner's live app. Run **30 buyer tasks** ("my car is navy and orange, pick finishes for stripes/hood/numbers", "make it feel like a night race car", "something like X but calmer", "I can't tell matte from satin, show me") using `spb_suggest_finishes`, `spb_find_finishes`, `spb_finish_details`, `spb_compare_finishes`, `spb_apply_scheme`, `spb_edit_zone`. Record where you were confused, where a tool result was misleading or too long, which calls were wasted, and what you wished a tool returned.
**Output:** `l7_mcp_tier/transcripts/` (one file per task), `l7_mcp_tier/report.md` (confusions ranked, proposed rewritten tool descriptions as a JSON map `{tool_name: "new description"}`, proposed new fields for results). Do not edit `tools.json` or the server.

---

## Hand-back protocol
- Each lane ends with an entry in `_codex_work/finish_intel/HANDOFF.md`: lane, files, counts, what you verified by eye, known gaps.
- Claude merges: L1 → re-annotate flagged cards + re-judge; L2 → new "truth" scorer next to the picture judge; L3 → classifier fixes measured against the corpus; L4 → lexicon/colour tables in `js/spb-ai-cards.js` and `js/spb-pro-design.js`; L5 → the gap list goes to the owner as the finish-authoring worklist; L6 → fixes + tests adopted; L7 → tool descriptions rewritten.
- Wiki: ONE board row for your lane (delete or compress it when done) and ONE daily-log entry (≤6 bullets). Details live in your own HANDOFF.md.
