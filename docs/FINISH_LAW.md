# THE FINISH LAW — the rule in stone

**Owner mandate, 2026-08-31.** Binding on every agent, every finish, forever.

> *"there needs to be a rule written in stone that makes sure we don't make this
> kind of mistake ever again building finishes. Even if you have to write a new
> formula for judging finishes."*
>
> *"HOW do we keep this from happening and continue to build ALL UNIQUE
> finishes? This should NOT be that hard. I don't care if it takes you 20
> minutes PER FREAKING FINISH — if you are making them truly UNIQUE and
> LEGENDARY, the time is worth it."*

---

## 0. What went wrong, so nobody repeats it

FRACTURED ELEMENTS shipped 60 finishes on **5 spec decks** — the deck was a
property of the *chapter*, not the finish, and there were **zero** per-finish
spec overrides. Twelve finishes dealt an identical material set and differed
only in palette and noise phase.

It passed its gate. That is the important part.

The lane verifier compared finishes with a **phase-sensitive cosine** over a
z-scored 32×32 grid. Re-running one generator with a new seed moves every
pixel, so a pure re-seed scored ~0.2 — "totally unique". ELEMENTS measured
**0 duplicates, max similarity 0.693** on a sheet the owner called *"totally
the same just slightly recolored"*.

The same law, measured properly, scores those finishes at **twin 0.98–0.99**.

**The lesson is not "check harder". It is: a metric that cannot see the failure
mode is not a gate, and reporting green from it is worse than not measuring at
all.** Two rules follow, and they are absolute:

1. **Never invent a threshold.** Fit it to owner verdicts (§4) and show the
   separation.
2. **Never report a gate as green without looking at a contact sheet at 1:1.**
   Every failure in this project's history was visible instantly by eye.

---

## 1. The five axes

Run: `python scripts/spb_finish_law.py --group "<name>"` (non-zero exit = FAIL).

| axis | what it asks | gate |
|---|---|---|
| **SCALE** | Is there real detail in the window the eye sees on a car (features 8–32px at 2048)? | `fine = max(paint_band, spec_band) >= 0.20` |
| **FOLLOW** | Does the spec's structure sit *on* the artwork's structure? | `amp_corr >= 0.35` |
| **STORY** | Does this finish own its material story, or share a deck? | shelf `story_ratio >= 0.90` |
| **TWIN** | Phase-invariant distance to the nearest sibling. | `< 0.80` |
| **PROTECTED** | Is this finish locked? | see `scripts/protected_finishes.json` |

### SCALE — measured on paint **or** spec

The owner's most repeated complaint: *"the patterns are just way way way too
big"*, *"not feasible to use in their current state"*.

Critically, the window may be satisfied by **either** channel. DICHROIC SKIN is
a gold standard whose *paint* is broad (band 0.040) because it is a smooth
colour-shift film — all its fine detail is in the **spec** (0.441). A finish is
only too big when *both* are too big. Gating on paint alone would have deleted
one of the owner's untouchable finishes.

### FOLLOW — the TRUCHET GLASS axis

> *"TRUCHET GLASS is a design that 1000x percent works. The design element and
> the way the spec map is on this one just WORKS ... UNIQUE design with a spec
> map that follows the design."*
>
> *"look at STATIC BLOOM for a good example of chaotic but makes no sense. The
> pattern just won't work on the car paint ... with the spec color pattern
> there being a problem."*

`amp_corr` correlates the **band-limited amplitude envelopes** of paint and
spec: *where the artwork has detail, does the spec also have detail?* It does
not demand that bright paint means rough spec — only that the spec is laid out
on the artwork rather than scattered independently across it.

**Band-limiting is not optional.** The first version compared raw per-pixel
gradients and scored TRUCHET GLASS at 0.134 — below finishes the owner
rejected. Restricted to the car window, TRUCHET scores **0.844, the highest in
the set**. Measure where the customer looks.

### STORY — derived from the render, not the source

A material story is the set of quantised (M, R, Cc) cells holding ≥1% of the
canvas. Two finishes dealing the same cards land on the same signature *no
matter how the recipe table is arranged*, so this cannot be dodged by moving
code around. This is the axis that catches a recolour matrix.

---

## 2. Protected finishes — never change

`scripts/protected_finishes.json` is law. **Hologram Metal**, **Dichroic
Skin**, **Truchet Glass**, **Cinder Pulse**, **Hologram Noir**. Do not edit
their renderers, recipes, palettes or decks; do not "optimise", re-gate or
re-bake them. Owner: *"It needs to be protected and NEVER CHANGED - at all
costs."*

**Exemptions are named, reasoned and rare.** HOLOGRAM METAL is exempt from
FOLLOW (it measures −0.004) because its mechanism *is* spec-independence:
micro-zones of contrasting spec materials that make colour shift and dance.
That is written down with the owner's quote. Adding another exemption requires
an owner verdict quoted in the file — never an agent's own judgement.

---

## 3. Authoring rules that follow from the law

1. **One finish, one material story.** The spec deck is a property of the
   FINISH, never of the chapter, lane, family or shelf. If your recipe table
   has a `CHAPTER_SPEC`-shaped thing in it, you have already failed.
2. **The spec is drawn from the artwork's own geometry**, not from an
   independent noise field dealt over the top of it.
3. **A recolour is not a finish.** New palette + same structure + same deck =
   the same finish.
4. **Design in the 8–32px window**, or put the detail in the spec deliberately
   and say so.
5. **Look at it at 1:1** before calling it done.

---

## 4. Calibration — how the thresholds were set

Thresholds are fitted to the owner's own verdicts, recorded verbatim in
`scripts/finish_law_labels.json`, and re-checked with:

```bash
python scripts/spb_finish_law.py --calibrate
```

Owner-labelled set (2026-08-31): 5 PASS (the gold standards), 4 PROMISE, 19
FAIL (named in the owner's message).

**Result: 20/24 agreement. All 5 gold standards pass. 15/19 rejects caught by
SCALE + FOLLOW; the remaining 4 are twins caught by TWIN/STORY.**

If a future change makes the law disagree with an owner verdict, **the law is
wrong, not the owner.** Re-fit it and record the new verdicts in the labels
file.

---

## 5. Definition of done

A finish is done when `spb_finish_law.py` exits zero for its shelf **and** a
1:1 contact sheet has been looked at. Neither alone is sufficient. Anything
else — including "the gate went green" — is not done.


## Amendments 2026-09-02 (reassessment on the PARADIGM 2048 sheets)

### COVERAGE is the sixth axis — `MAX_DEAD = 0.70`
`ash_chrome`, `soot_pearl` and `cinder_mirror` were nearly solid black at 2048
and PASSED every axis: SCALE is happy with fine detail on 5% of the canvas, and
FOLLOW correlates trivially when both envelopes are near zero. CLAUDE.md rule 0b
already mandated full-canvas coverage; the law had omitted it. `coverage_axis()`
measures the fraction of the paint whose luma is < 0.06 or > 0.94. Calibration
after adding it: still 20/24, all five gold standards pass (Cinder Pulse is the
darkest at 0.45 dead, well inside the line).

### Mutual information is NOT a FOLLOW axis — measured and rejected
Bark and corrugate looked, on the sheet, as if their specs followed their creases
while scoring FOLLOW 0.019 and 0.067. The tempting fix was `amp_corr >= 0.35 OR
nmi >= t`. Measured against the owner's labels: NMI does not separate PASS from
FAIL (Flow Tubes, an owner FAIL, scores 0.347; three gold standards sit at
0.18-0.21) and every threshold from 0.10 to 0.30 drops agreement from 20/24 to
14/24 or worse. Rejected. Both measures were also low on bark/corrugate, so the
glance was wrong and the numbers were right: the spec was not on the creases.

### The real fix for dense textures: `spec_story.compose(..., micro="paint")`
On a texture that is equally busy everywhere, an independent micro grain cannot
follow anything. `micro="paint"` derives the spec's fine layer from the paint's
own car-band detail (bandpass of the rendered paint luma), so the material change
sits on the paint's crease. This is what "the spec follows the design" means for
bark, corrugate, canvas, denim — any texture without sparse structure.

### Gate green is necessary, not sufficient — reaffirmed
Every one of these was found by looking at a 1:1 sheet (`scripts/spb_visual_verify.py`),
not by a metric. A maze construction for "cinder" passed every axis and read as a
maze. Look at every shelf at 2048 before calling it done.
