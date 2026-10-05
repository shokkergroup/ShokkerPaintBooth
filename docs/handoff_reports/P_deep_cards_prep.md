# P - deep cards prep (2026-10-03)

## Step 1 (published): spec patterns + patterns, no grouping needed
- Actual counts in items.json differ from the brief: **spec 301** (not 181), **pattern 319** (not 329), base 1144, monolithic 3035 (total 4799).
- `python scripts/ai_atlas/deep_plan.py --stage 1` -> `_atlas_deep/plan.json` + shards 001-006 (spec, ~50 each) and 007-012 (pattern, ~54 each); type-pure, balanced <=60, QA-flagged first (0 of the spec/pattern units are flagged: all 193 flags are bases/monolithics).
- Every unit has a picture: spec = 194x64 strips (`_atlas_cards/thumbs/spec__*.png`), pattern = 128x128 (`thumbnails/pattern/*.png`), 2 at 128x64. no_picture = 0. Pictures are small; writers should say so in confidence when detail is not readable.
- Units carry numbers (spec patterns have null L/S/V/M/R/C/sp/shine/metal - only fb/an/tags exist for them), trimmed old card, qa.

## Step 2 (published): `_atlas_deep/RUBRIC.md` with two worked examples (pattern shokk_cipher_pattern, spec spov2_alligator_coat), written from the pictures. Note for writers: spec pictures are 3-panel M|R|Cc strips.

## Step 3: family grouping + full plan (`python scripts/ai_atlas/deep_plan.py`)
- Rule: base/monolithic members group when type + NAME STEM (parenthetical and trailing colour words removed) + `fb` fineness + `shine` class all match. Everything else is its own unit; spec/pattern never grouped.
- Result: **4,722 units** (spec 301, pattern 319, base 1,138, monolithic 2,964) = **81 shards** (001-006 spec, 007-012 pattern, 013+ base then monolithic, balanced <=60, QA-flagged first, then appeal+hero descending). 18 families (sizes 2:11, 3:1, 4:2, 5:1, 10:1, 15:1, 32:1); family units name "<stem> (family of N)". Honest note: this catalogue's names are mostly unique ("Cs Amber Indigo", "Indigo Tsunami"), so grouping only saves 77 units; the 32-member "cs" family is one construction in many colour pairs. Further merging would need image similarity and was not attempted.
- no_picture = 0. Image px: 128x128 (3,804 units), 194x64 spec strips (301), 256 (351), 512 (221), 128x64 (32), 64 (13). All from existing thumbnails; nothing fetched.
- QA flags: 193 = monolithic 129, base 46, pattern 18, spec 0. Flagged units need `qa_fix`.

## Step 4: `deep_validate.py` and `merge_deep_cards.py` written and tested with the two worked examples (temp file, removed): validator OK, merge dry run changed 1-2 cards (spec example merged; look gets look_far appended, syn gets asks; `look0`/`syn0` keep the originals so re-runs are idempotent). `not` / avoid_asks deliberately not indexed.
Rebuild sequence after `merge_deep_cards.py --write` (NOT run): `python scripts/ai_atlas/build_cards_js.py` (also chains build_lsa.py -> lsa_tf dump + js/spb-lsa-data.js) -> bump `window.SPB_CARDS_V` default in js/spb-ai-cards.js and the `?v=` tokens of spb-ai-cards-data.js / spb-lsa-data.js / spb-ai-cards.js in paint-booth-v2.html -> `node scripts/sync-runtime-copies.js --write` then `--check`. `deep` itself is not shipped by build_cards_js.py (needs a JS change to read it).
