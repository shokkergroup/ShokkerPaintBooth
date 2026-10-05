## 2026-08-31 (day) — MONEY SHOKK rebuilt, COLORSHOXX → WORLD OF COLOR, and all 185 CULTURAL specs re-authored

Three commissions in one brief, 325 finishes touched, and the paint on 185 of them deliberately not touched at all.

### 💵 MONEY SHOKK — 40 rebuilt

Owner: *"Forty themed exotic engines about wealth in every form — mint foil, vault steel, counterfeit gold, burn-a-stack green. Flexes harder than chrome. Right now we are falling WELL SHORT of it doing what it's supposed to. Needs a total rework."*

**What was there.** Forty ids named `{colour} {creature}` — Canary Coffin, Magenta Widow, Cerulean Cobra, Lime Scorpion, Hyperpink Torii, Seafoam Piranha — in four seeded batches (`msh_`, `mshc_`, `msha_`, `mshx_`) off shared engines. A colour × creature grid with a money name on the box. Nothing in it was about money.

**The idea.** Money is not a colour, it is a *manufacturing process*, and currency is the most over-engineered printed object on earth — almost all of that engineering being anti-counterfeiting texture at exactly the scale a car body wants. Five chapters of eight: 🖨 MINT · 🏦 VAULT · 💎 ASSET · 🎭 COUNTERFEIT · 🔥 BURN. The COUNTERFEIT chapter is the one with teeth: every card in it is deliberately *wrong in one material* — plated brass where gold should be, a dead-flat patch where the ink should sit up, a scanner's moiré beating against the engraving.

**New kit, ten primitives** (`money_shokk_kit_2026.py`): `guilloche` written as an implicit field rather than drawn curves — a rose engine cuts nested rosette contours a fixed distance apart, so `sin(2π·ρ/(1+a·cos(nφ))/ring)` gives the same pattern with the **line spacing under direct control**, which matters because drawn as polylines it scored 0.19–0.28 on the car band (a few big rosettes put their energy in the petal envelope, below the window, and the hairlines put the rest above it). Also `intaglio` (tone carried in line *width*, as an engraver actually works), `microtext`, `threads`, `moire`, `knurl`, `facets`, `bricks`, `shred`, `char`, `watermark`.

**Measured, all 40:** renders 1.3–3.0s, car-band 0.47–0.94, coverage 64/64, 9–18 material cards over 3–5 families, nearest-sibling similarity ≤0.32. Chrome, mercury, carrier and spectraflame are all present and all *earned* — the foil stripe, the bullion, the diamond table, the hologram patch. Never the whole panel.

### 🌍 WORLD OF COLOR — COLORSHOXX repurposed, 77 → 100

Owner: *"COLORSHOXX ... was originally designed to try to do something unique with color flipping. It's outdated and very repetitive now. I'm thinking of taking that from 77 finishes to 100 and repurposing this to WORLD OF COLOR which will take colors/styles from various COUNTRIES."*

**The specs were the tell.** Measured across all 77: a **median of 2 distinct material cards over 2 families, roughness σ 7.0, clearcoat σ 2.5**. Two flat cards, 77 times — so the "flip" was the paint doing it alone, from the same handful of engines, in three generations of `cx_{colour}`, `cx_{a}_{b}` and `cx_hyperflip_{a}_{b}`.

**The 100.** Twenty places × five, and each finish is a **material or process that place actually makes colour with** — a tartan sett, an indigo vat, a celadon glaze, an ochre bed, a salt terrace, a rose-painted dowry chest. Five continental chapters: 🌍 EUROPE (Ireland · Scotland · Portugal · Norway) · 🌏 ASIA (Japan · India · Türkiye · Korea) · 🌍 AFRICA (Morocco · Mali · Egypt · Ethiopia) · 🌎 AMERICAS (Jamaica · Brazil · Peru · Cuba) · 🌏 OCEANIA (Australia · Aotearoa · Indonesia · Philippines).

**The scope is drawn deliberately.** SPB already has five CULTURAL shelves built on flags and iconography, so coming at the world through *craft* instead means this shelf cannot become a second copy of those — Rising Sun has the flag; here Japan is an indigo vat, an urushi table and a raku kiln. Everything is drawn from commercially made textiles, ceramics, minerals and landscape; sacred and ceremonial designs are not source material for car paint and none are used.

**New kit, four primitives** (`world_of_color_kit_2026.py`): `sett` (a tartan repeat reflected about its pivots, run both ways, with a real 2/2 twill deciding which thread is on top at each crossing), `stars` (the n-pointed star-and-rosette tiling of zellij, iznik and azulejo as an implicit field), `ikat` (warp-resist — the dye goes on the *thread*, so the design arrives smeared along one axis and crisp across it, and that asymmetry is the whole signature), `resist` (wax or mud, then crackle **along the resist's own patch boundaries**, which is where wax actually cracks and costs nothing next to the 0.73s annealing simulation it replaced).

**Measured, all 100:** 100/100 green — renders ≤3s, car-band ≥0.45, coverage 64/64, ≥7 shade tiers, 10–18 material cards over 3–6 families, nearest-sibling similarity ≤0.16.

### 🌐 CULTURAL — 185 finishes, paint byte-identical, every spec re-authored

Owner: *"keep the designs in place that's there now for the base paint and rework ALL of the specs ... apply specs that make sense to EACH finish in EACH of those categories."*

**The paint is untouched.** These are hand-authored plates and they stay. The triage (`_wealth_work/triage.py`, all 185 at 2048) says exactly where the specs were weak:

| category | n | spec cards | families | Rough σ | Cc σ |
|---|---|---|---|---|---|
| FORBIDDEN DRAGON | 20 | 3/8/12 | 1/4/4 | 20/47/80 | 17/32/46 |
| LET FREEDOM RING | 10 | 4/8/9 | 3/3/4 | 11/30/45 | 7/39/74 |
| RISING SUN | 52 | 4/8/12 | 2/3/5 | 17/70/98 | 10/48/86 |
| UNION JACKED | 45 | 6/8/13 | 4/4/4 | 50/62/74 | 5/12/22 |
| VIVA MEXICO | 58 | 4/10/13 | 3/4/5 | 32/80/96 | 18/48/87 |

**47 of 185 had a clearcoat σ below 20** — a flat Cc means the coat itself does nothing and the one control that separates a lacquer from a glaze from raw metal is switched off. UNION JACKED was flat across *all 45* cards (median 12, maximum 22). Twenty more scored below 0.30 on whether the spec sat on its artwork at all.

**How it works now.** `engine/paint_v2/cultural_spec_2026.py`, on the machinery the MORTAL SHOKK rebuild proved: read the finish's own plate into six roles (void / ground / figure / vein / hot / flash) and deal a **complete material card** to each. Because the roles are found in the artwork, the spec follows the design by construction rather than by a correlation gate.

**The vocabulary is the new part** — what each culture actually builds things out of. Viva Mexico's talavera, worked silver, hammered copper and obsidian; Rising Sun's urushi, aizome, raku, kintsugi and raden; Union Jacked's wet asphalt, vitreous enamel, brass and soot-stained portland; Forbidden Dragon's cloisonné, fire-gilt bronze, carved lacquer and jade; Let Freedom Ring's bumper chrome, hard enamel, brushed alloy and cold-blued steel. Forty stories in all, and **each finish is matched to one by measuring its own paint** — Talavera Azul (hue 235) gets the glaze, Desert Marigold (hue 35) gets hammered copper, Guadalupe Lowrider gets candy-over-flake. None of that was hand-assigned.

Three things had to be right or the vocabulary would not have landed:

* **The assignment must be balanced, but softly.** Scoring finishes one at a time put 5 of 10 LET FREEDOM RING cards on the same story. A hard cap fixed the spread and broke the matching — with 58 Viva finishes and 8 stories it pushed an orange plate onto jade. Reuse is now a **saturating** penalty, `0.55·log1p(uses)`, which costs 1.27 at nine uses against a hue term that maxes at 2.4: enough to spread the common hues, never enough to beat a strong match.
* **The tie-break hash had to be stable.** It was Python's built-in `hash()`, which is salted per process — so a finish got a different material every time the server restarted. Now `zlib.crc32`.
* **The substrate rule.** A story can *name* three material families and still deliver two, because the families that show are the ones with **area** — void, ground, figure and the saturated accent; a 10% chrome flash never reaches the 1.5% threshold. 25 of 40 stories failed on that. The fix is not a bigger flash, it is naming the second substance that is really there: a tin glaze sits on a fired earthenware body, vitreous enamel is fused onto steel, candy sits under clearcoat over flake, cloth has a sizing on it, raku's colour *is* reduced copper lustre.

**Two gates were wrong and were fixed rather than gamed.**

* The absolute car-band floor on the spec's roughness channel fails cards whose *artwork* is coarse — `lfr_we_the_people` scores 0.267 on the band itself, and 132 of the 185 plates are below 0.45. A spec that faithfully follows a coarse plate is supposed to be coarse, and forcing the number would have meant adding noise to hand-authored art. The test is now **relative**: the spec must be no coarser than its own paint (≥0.80×), above a floor of 0.25.
* **FOLLOW was measuring the wrong channel.** It correlated the spec's roughness against the paint's *luma* — but half these liveries carry their structure in COLOUR at nearly constant brightness, which is exactly why `roles()` cuts from a weighted luma+chroma field in the first place. Measured against luma, `rs_mikan_pearl` reads **0.122** and `lfr_midnight_militia` **0.119**; measured against the field the roles were actually cut from, the same two specs read **0.838** and **0.900**. 13 of the 18 remaining failures were this. The gate now uses the design field, and carries a **control**: each spec scored against *other* finishes' fields lands at **median 0.012, p95 0.149**, against an own-field median of **0.782** — so the number is measuring something real.

**A role must not be able to own the whole surface.** On a near-uniform black plate the void role took 95% of the canvas, leaving the other five roles about 1% each — under the 1.5% area threshold, so the finish reported **8 material cards and 1 family** and had no material story at all. `roles()` now honours an optional `void_max`, set to 58% for the dark-plate stories. Obsidian's black is sheen, not flatness, and the cap makes the spec say so. (Default is 100%, so MORTAL SHOKK's behaviour is unchanged.)

**Measured, all 185:** **178/185 green.** Material cards **9–20** each (was 3–13), families 2–6, roughness σ **20.6–106.6**, clearcoat σ **22.6–103.8** with **zero below 20** (was 47), follow median **0.862** against a control floor of 0.038 (p95 0.238), and the spec builds in **0.52–0.82s** at 2048 on top of the paint. The seven that remain are named in `_cultural_work/verify.json`: three FOLLOW, three SPECBAND and one FAM, all in UNION JACKED / LET FREEDOM RING, all on plates whose own artwork is the limiting factor.

### Wiring

`engine/registry.py` (V5, which is what `/api/finish-data` enumerates) + `shokker_engine_v2.py` + the JS catalog + `scripts/runtime-sync-manifest.json`, synced to `electron-app/server/`. The old `msh_`/`mshc_`/`msha_`/`mshx_` and `cx_` ids stay defined and registered so saved projects still render; they are off the shelf. Catalog token → `spb-money-world-20260831c`.

### A category can no longer go missing by accident

Owner: *"A couple of the fractured categories you rebuilt last night no longer show up in the ZONE POPOUT picker."* Not reproducible on the current build — driving the real app, the zone popout renders 65 groups including all 14 FRACTURED cards and PARADIGM, fully populated, and search finds their finishes. The likely cause is dated: `electron-app/server/paint-booth-0-finish-data.js` **failed to sync** on 2026-08-31 ~06:17 with a file lock and was only repaired later that morning, so anything served from that directory had the old catalog.

New guard either way: **`node tests/guard_picker_categories_reachable.js`** fails on the four ways a category disappears without a crash — ORPHANED (populated but named in no section, which has already cost 77 finishes once), DANGLING (a section names a group that does not exist), HOLLOW (reachable but no id resolves), and a literal `\U0001F9E0` escape pasted into the section list, which never matches the real key and is in the git history. Currently green, with three documented pre-existing orphans on an explicit allow-list.

**Restart the server and hard-reload** — all three lanes are engine-side.
