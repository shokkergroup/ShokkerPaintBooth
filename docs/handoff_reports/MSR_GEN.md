# MSR-GEN: mad scientist ask generation (worker report)

File: `scripts/ai_atlas/mad_asks.jsonl` (append-only, B1 `expect` schema, ids M001..). Generated in batches of 50, each appended immediately; duplicates of B1's 200 and of earlier M asks are rejected by normalised text.

Total asks: **610** in 12 batches.

## Counts by class

- typo_slang: 67
- stack2: 55
- animal: 51
- scale: 46
- constraint: 45
- placement: 41
- weather_light: 40
- material_mashup: 39
- absurd_but_answerable: 36
- stack3: 32
- brand_free_lookalike: 30
- era_vibe: 28
- mood_stack: 24
- question: 21
- negated_stack: 20
- like_but_stack: 20
- ambiguous: 15

## Matrix coverage (heuristic, from expect + ask words)

- **base**: flat 241, matte 94, - 85, metallic 47, candy 45, pearl 37, chrome 27, satin 22, sparkle 12
- **pattern**: none 194, scales 74, geometric 71, camo 69, stripes 48, weave 39, other 33, hex 33, flames 20, marble 17, splatter 12
- **shine**: none 395, flake 57, other 38, wet 38, frosted 24, brushed 21, pearl 20, hammered 17
- **colour**: named 232, none 230, two 100, recolor 24, current 15, hex 9
- **place**: whole 520, hood 34, roof/stripes 23, other-part 21, numbers 12
- **constraint**: none 538, subtle 23, keep 17, loud 12, classy 10, not-cheap 5, no-chrome 5

## Slider-move asks (move words in the ask; the schema cannot encode the move itself)

41 asks: M114, M115, M116, M117, M118, M119, M120, M121, M122, M125, M126, M127, M132, M267, M331, M370, M371, M372, M373, M374, M375, M376, M377, M378, M379, M380, M382, M383, M384, M454, M455, M456, M538, M539, M540, M541, M542, M543, M544, M545, M586

## Facet words introduced beyond B1

`animal`, `spots`, `marble`, `splatter`, `wood`, `ice`, `frost`, `hammered`, `neon`, `rainbow`, `organic`, `floral` as pattern/base/spec classes where B1 had no word; scorers should treat unknown words as free text matched against item name/tags.

## Schema gaps

- No field for a slider move (hue/finer/dial back) or its direction; slider asks are only identifiable by wording, `scale` covers finer/coarser only.
- No field for a target colour (hex or name) or for 'recolour only the camo, keep the rest'.
- No field for layer order (marble UNDER candy) or for 'no base change, spec only'.
- `base_class` mixes colour and look; a two-colour ask cannot say which colour goes where.
- Brand lookalikes have no 'must not name the brand' flag (expect only must_not words).
