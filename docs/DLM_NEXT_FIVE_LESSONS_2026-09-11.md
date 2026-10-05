## Owner location and PSD delivery rule — 2026-09-11

All future livery production work belongs under `C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/1-Shokker Paint Booth Working/FORGE PROJECT`. Do not create car working directories in the main SPB application folder. This batch now lives at `C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/1-Shokker Paint Booth Working/FORGE PROJECT/Next Five DLMs 2026-09-11/_WORKING`; candidate history, assets, caches, scripts and shared template/export inputs moved with it. Main SPB retains only central Wiki and compact learning notes.

Every car delivery must visibly link all three Photoshop variants: Detailed (individual placed elements), 8-layer Tidy, and 3-layer Simple. Do not hide alternatives behind an 8-layer-only gallery link. Complete artwork remains underneath movable numbers and sponsors. These five already had all 15 PSDs; access links were missing, not the files. Four detailed PSDs have 37 layers; Pool Coping has 36. Native Photoshop acceptance remains unverified.

Original build/proof receipts retain historical source paths. RELOCATION_RECEIPT.json maps the old batch directory to _WORKING and records byte preservation; relative scene paths and original artwork bytes remain unchanged.

# Lessons from the next five DLMs — 2026-09-11

Completed for owner review: Eagle Foundry18 v003, Rail Yard46 v002, Pool Coping54 v001, Screaming Cerulean85 v002, Dot Comet73 v002. Each has paint/spec, detailed + 8-layer tidy + 3-layer PSDs, six Studio proofs and ten reference sheets. This is saved workflow knowledge, not model weight training or owner acceptance.

## What became reusable

1. **Keep the template fixed and the art unique.** Reuse the approved full physical masks, measured decal placement, number/deck orientations, protected baseline and uniform three Shokker-hand positions. Cache fender coordinates once. Nine declared full targets passed on every final candidate, including deck, roof, front, lower returns and paintable tub/collar. This does not certify unknown islands.
2. **Make the complete art before the decals.** Continuous side/hood/deck/roof/tub backgrounds remain under separate numbers and sponsors. Actual PSD decoding and number-move tests exposed 58k–65k pixels per car with zero RGBA backing error. The 8-layer PSD is the practical default; detailed and 3-layer alternatives are supplied.
3. **Design names and slogans up front.** Number/title/concept-tagline sheets and a shared five-row SPB slogan sheet gave each scheme its own styled lettering. Actual Antihero/Santa Cruz source logos and the supplied exact Shokker hand were reused, with source provenance.
4. **Reject source problems before mapping.** Require rectangular full-bleed print fields without wheels, car silhouettes or white sheet ground. Rail and Screaming needed per-column artwork rectification because light margins contaminated the fenders. Do not mistake that artifact for a body-geometry hole.
5. **Treat fenders as their own art region.** Eagle's first front-only sampling clamp still left cream/black shoulder patches. Reusing its uninterrupted gold engraving field for both fenders removed them; Studio front/top views verify the final v003. No model edits or repeated image generation were required for that repair.
6. **Inspect extracted decals on contrasting backgrounds.** Dot's navy threshold retained two disconnected dark fragments beside the 73. Keeping the two inspected glyph components, without changing source bounds, removed the fragments on both sides and roof. Component-count rules are design-specific; do not blindly delete intentional punctuation or detail from other numbers/logos.
7. **Review before final PSD export.** I exported several early candidates during review and then had to repeat exports. That was avoidable work. Next run: first freeze the visible candidate, then export PSD variants once. Keep candidate hashes in proof receipts so stale images cannot masquerade as the final paint.
8. **Reuse actual assets for ten sheets.** Ten deliverable reference sheets do not need ten independent image-generation calls when the needed art already exists. Assemble the final sheets from isolated working assets and actual Studio renders. Keep prompts, originals, masks and editable sources alongside them.

## Measurements and limits

Initial assembly times were 25.97, 19.95, 20.98, 18.55 and 17.32 seconds. These are compiler/assembly times after artwork preparation, not full-car turnaround. The first-to-last drop is not evidence of the same end-to-end improvement: source generation, cleanup and review dominated this roughly three-hour batch, and repeated exports added work. Final PSD export/checks took approximately 63–72 seconds per car. Future comparisons must record asset preparation, mapping, correction, review and export separately.

All native paint/spec and PSD masters are 2048-square. Studio proofs and reference-sheet canvases are 3840x2160. Generated sheets were 1672x941; enlargement does not make their detail native 4K. Native Photoshop and iRacing application checks were not performed. Studio remains approximate, especially tub UVs. No independent-user repeatability or owner approval of these five is claimed.

## Next-five order of work

Concept inspection and unique-art plan → original logos + full print fields + designed lettering → source-edge/alpha review → reuse physical masks and placements → compile → inspect both sides/top/front/rear and flat Wire → one grouped visible correction pass if needed → final PSD export/backing check → ten sheets and review gallery. Preserve finished regions; another correction needs a named visible defect.
