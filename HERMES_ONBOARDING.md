# Hermes Onboarding Prompt for SPB

## PASTE THIS INTO HERMES (all at once):

---

You are being onboarded onto the Shokker Paint Booth (SPB) project. This is a DEEP DIVE — read everything I tell you to, understand the architecture completely, and remember it permanently. Every future session depends on what you learn right now.

The workspace is /mnt/e/Koda/Shokker Paint Booth Gold to Platinum. Use FULL ABSOLUTE PATHS for every file operation.

## PHASE 1: Read the project docs (do ALL of these)

1. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/HERMES.md — your quick reference
2. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/CHANGELOG.md (first 80 lines) — recent work history
3. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/PRIORITIES.md (first 60 lines) — what's being built
4. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/OPEN_ISSUES.md — current bugs
5. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/QA_REPORT.md — QA findings
6. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/SHOKKER_BIBLE.md (first 50 lines) — brand rules

## PHASE 2: Understand the architecture

READ these files to understand how the paint engine works:

7. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/engine/base_registry_data.py (first 40 lines + lines 260-310) — how bases are registered. Each base has M (metallic), R (roughness), CC (clearcoat), a paint_fn, and optionally a base_spec_fn.

8. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/engine/spec_paint.py (lines 1-20 + lines 745-760 + lines 3269-3280) — the main spec/paint function library. Hundreds of functions that generate spec maps and modify paint.

9. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/engine/chameleon.py (lines 197-242) — spec_chameleon_v5 is the BEST example of how spec functions should work. M inversely correlated with field, CC opposing M, micro-flake variation.

10. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/engine/paint_v2/structural_color.py (first 60 lines + lines 250-310) — COLORSHOXX system. 25 color-shifting finishes with married paint+spec pairs.

11. Read /mnt/e/Koda/Shokker Paint Booth Gold to Platinum/paint-booth-0-finish-data.js (lines 1508-1560) — BASE_GROUPS categories that define the picker UI.

## PHASE 3: Learn the critical rules

After reading, MEMORIZE these rules permanently:

**RULE 1: 3-COPY SYNC** — Every file in engine/ exists in 3 places. After ANY edit, copy to all 3:
- engine/ (root — this is the source of truth)
- electron-app/server/engine/ (server copy)
- electron-app/server/pyserver/_internal/engine/ (internal copy)
Use: cp source dest1 && cp source dest2

**RULE 2: GGX ROUGHNESS FLOOR** — The R (roughness/Green) channel in spec maps must be >= 15 for non-chrome bases. Chrome bases (M >= 240) can have R = 0-10. Every np.clip on R should use 15 as the lower bound, not 0. This prevents iRacing's GGX whitewash artifact.

**RULE 3: PAINT+SPEC MARRIAGE** — For special finishes, the paint function and spec function should use the SAME noise seeds so their spatial fields align. The paint creates STATIC color. The spec controls HOW the renderer lights it (M=metallic flash, R=roughness, CC=clearcoat). The RENDERER handles angle-dependent effects, NOT the paint function.

**RULE 4: NO LAZY FINISHES** — Every pattern, finish, and spec overlay must be genuinely distinct. No copy-paste with different constants. No paint_none on special finishes. No shared spec functions where custom ones are needed.

**RULE 5: CHANGELOG EVERYTHING** — Every code change gets logged to CHANGELOG.md at the TOP of the file with: Author, Issue, What changed, Why, Files modified, Verification notes.

**RULE 6: iRacing Spec Map Channels:**
- R (Red) = Metallic (0=dielectric, 255=chrome mirror)
- G (Green) = Roughness (0=mirror smooth, 255=dead rough) — GGX floor at 15
- B (Blue) = Clearcoat (16=max gloss, 255=dead flat matte)
- A (Alpha) = Spec mask

## PHASE 4: Understand the codebase scale

Run these commands to get a sense of scale:
- grep -c "texture_fn" /mnt/e/Koda/Shokker\ Paint\ Booth\ Gold\ to\ Platinum/shokker_engine_v2.py — pattern count
- wc -l /mnt/e/Koda/Shokker\ Paint\ Booth\ Gold\ to\ Platinum/engine/spec_paint.py — main spec file size
- wc -l /mnt/e/Koda/Shokker\ Paint\ Booth\ Gold\ to\ Platinum/shokker_engine_v2.py — core engine size
- ls /mnt/e/Koda/Shokker\ Paint\ Booth\ Gold\ to\ Platinum/engine/paint_v2/ — paint v2 modules
- ls /mnt/e/Koda/Shokker\ Paint\ Booth\ Gold\ to\ Platinum/engine/expansions/ — expansion modules

## PHASE 5: Summarize what you learned

After reading everything, write a summary of:
1. What SPB does (1 paragraph)
2. How the paint+spec system works (2-3 paragraphs)
3. The key files and what each does (bullet list)
4. The current state — what was just completed, what's next
5. The 3 most important rules you must never violate
6. What COLORSHOXX is and how it works

This summary is your PERMANENT KNOWLEDGE BASE for all future SPB sessions. Remember it.

## PHASE 6: Extract skills

After summarizing, create these as reusable workflows in your memory:
- "SPB file edit" — edit a Python file + sync 3 copies + log to CHANGELOG
- "SPB base audit" — read a base entry, check M/R/CC values, check paint_fn, check spec_fn, verify GGX
- "SPB spec function check" — read a spec function, verify R >= 15 clips, verify it complements its paint function

These should become automatic skills you use in every future session.
